# Copyright 2012 OpenStack Foundation
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 - 2012 Justin Santa Barbara
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from keystone.common import utils
from keystone.common import wsgi
from keystone import exception
from keystone.i18n import _, _LW
from keystone.models import token_model
from keystone.openstack.common import log

AUTH_CONTEXT_ENV = 'KEYSTONE_AUTH_CONTEXT'
"""Environment variable used to convey the Keystone auth context.

Auth context is essentially the user credential used for policy enforcement.
It is a dictionary with the following attributes:

* ``user_id``: user ID of the principal
* ``project_id`` (optional): project ID of the scoped project if auth is
                             project-scoped
* ``domain_id`` (optional): domain ID of the scoped domain if auth is
                            domain-scoped
* ``roles`` (optional): list of role names for the given scope
* ``group_ids``: list of group IDs for which the API user has membership

"""

LOG = log.getLogger(__name__)


def token_to_auth_context(token):
    if not isinstance(token, token_model.KeystoneToken):
        raise exception.UnexpectedError(_('token reference must be a '
                                          'KeystoneToken type, got: %s') %
                                        type(token))
    auth_context = {'token': token,
                    'is_delegated_auth': False}
    try:
        auth_context['user_id'] = token.user_id
    except KeyError:
        LOG.warning(_LW('RBAC: Invalid user data in token'))
        raise exception.Unauthorized()

    if token.project_scoped:
        auth_context['project_id'] = token.project_id
    elif token.domain_scoped:
        auth_context['domain_id'] = token.domain_id
    else:
        LOG.debug('RBAC: Proceeding without project or domain scope')

    if token.trust_scoped:
        auth_context['is_delegated_auth'] = True
        auth_context['trust_id'] = token.trust_id
        auth_context['trustor_id'] = token.trustor_user_id
        auth_context['trustee_id'] = token.trustee_user_id
    else:
        auth_context['trust_id'] = None
        auth_context['trustor_id'] = None
        auth_context['trustee_id'] = None

    roles = token.role_names
    if roles:
        auth_context['roles'] = roles

    if token.oauth_scoped:
        auth_context['is_delegated_auth'] = True
    auth_context['consumer_id'] = token.oauth_consumer_id
    auth_context['access_token_id'] = token.oauth_access_token_id

    if token.is_federated_user:
        auth_context['group_ids'] = token.federation_group_ids

    return auth_context


def _build_policy_check_credentials(token_provider_api,
                                    action, context, kwargs):
    LOG.debug('RBAC: Authorizing %(action)s(%(kwargs)s)', {
        'action': action,
        'kwargs': ', '.join(['%s=%s' % (k, kwargs[k]) for k in kwargs])})

    # see if auth context has already been created. If so use it.
    if AUTH_CONTEXT_ENV in context.get('environment', {}):
        LOG.debug('RBAC: using auth context from the request environment')
        return context['environment'].get(AUTH_CONTEXT_ENV)

    # There is no current auth context, build it from the incoming token.
    # TODO(morganfainberg): Collapse this logic with AuthContextMiddleware
    # in a sane manner as this just mirrors the logic in AuthContextMiddleware
    try:
        LOG.debug('RBAC: building auth context from the incoming auth token')
        token_ref = token_model.KeystoneToken(
            token_id=context['token_id'],
            token_data=token_provider_api.validate_token(
                context['token_id']))
        # NOTE(jamielennox): whilst this maybe shouldn't be within this
        # function it would otherwise need to reload the token_ref from
        # backing store.
        wsgi.validate_token_bind(context, token_ref)
    except exception.TokenNotFound:
        LOG.warning(_LW('RBAC: Invalid token'))
        raise exception.Unauthorized()

    auth_context = token_to_auth_context(token_ref)

    return auth_context


def check_protection(token_provider_api, policy_api, action, context,
                     input_attr, target_attr):
    # TODO(henry-nash) need to log the target attributes as well
    creds = _build_policy_check_credentials(
        token_provider_api, action, context, input_attr)
    # Build the dict the policy engine will check against from both the
    # parameters passed into the call we are protecting (which was
    # stored in the prep_info by protected()), plus the target
    # attributes provided.
    policy_dict = {}
    if target_attr:
        policy_dict = {'target': target_attr}
    policy_dict.update(input_attr)
    policy_api.enforce(creds, action, utils.flatten_dict(policy_dict))
    LOG.debug('RBAC: Authorization granted')


# controller is only used for get_member_from_driver and should be passed as
# None otherwise
def protect(controller, member_name, token_provider_api, policy_api, action,
            context, kwargs):
    creds = _build_policy_check_credentials(
        token_provider_api, action, context, kwargs)
    policy_dict = {}

    # Check to see if we need to include the target entity in our
    # policy checks.  We deduce this by seeing if the class has
    # specified a get_member() method and that kwargs contains the
    # appropriate entity id.
    if controller:
        key = '%s_id' % member_name
        if key in kwargs:
            ref = controller.get_member_from_driver(kwargs[key])
            policy_dict['target'] = {member_name: ref}

    # TODO(henry-nash): Move this entire code to a member
    # method inside v3 Auth
    if context.get('subject_token_id') is not None:
        token_ref = token_model.KeystoneToken(
            token_id=context['subject_token_id'],
            token_data=token_provider_api.validate_token(
                context['subject_token_id']))
        policy_dict.setdefault('target', {})
        policy_dict['target'].setdefault(member_name, {})
        policy_dict['target'][member_name]['user_id'] = (
            token_ref.user_id)
        try:
            user_domain_id = token_ref.user_domain_id
        except exception.UnexpectedError:
            user_domain_id = None
        if user_domain_id:
            policy_dict['target'][member_name].setdefault(
                'user', {})
            policy_dict['target'][member_name][
                'user'].setdefault('domain', {})
            policy_dict['target'][member_name]['user'][
                'domain']['id'] = (
                    user_domain_id)
    # Add in the kwargs, which means that any entity provided as a
    # parameter for calls like create and update will be included.
    policy_dict.update(kwargs)
    policy_api.enforce(creds, action, utils.flatten_dict(policy_dict))
    LOG.debug('RBAC: Authorization granted')


def filter_protect(controller, token_provider_api, policy_api, filters,
                   context, action, **kwargs):
    creds = _build_policy_check_credentials(token_provider_api,
                                            action,
                                            context, kwargs)
    # Now, build the target dict for policy check.  We include:
    #
    # - Any query filter parameters
    # - Data from the main url (which will be in the kwargs
    #   parameter) and would typically include the prime key
    #   of a get/update/delete call
    #
    # First  any query filter parameters
    target = dict()
    if filters:
        for item in filters:
            if item in context['query_string']:
                target[item] = context['query_string'][item]

        LOG.debug('RBAC: Adding query filter params (%s)', (
            ', '.join(['%s=%s' % (item, target[item])
                      for item in target])))

    # Now any formal url parameters
    for key in kwargs:
        target[key] = kwargs[key]

    policy_api.enforce(
        creds, action, utils.flatten_dict(target))

    LOG.debug('RBAC: Authorization granted')
