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

from oslo_config import cfg
from oslo_log import log
from oslo_utils import strutils

from keystone.common import utils
from keystone import exception
from keystone.i18n import _LI
from keystone.i18n import _, _LW
from keystone.models import token_model


CONF = cfg.CONF


AUTH_CONTEXT_ENV = 'KEYSTONE_AUTH_CONTEXT'
"""Environment variable used to convey the Keystone auth context.

Auth context is essentially the user credential used for policy enforcement.
It is a dictionary with the following attributes:

* ``token``: Token from the request
* ``user_id``: user ID of the principal
* ``user_domain_id`` (optional): Domain ID of the principal if the principal
                                 has a domain.
* ``project_id`` (optional): project ID of the scoped project if auth is
                             project-scoped
* ``project_domain_id`` (optional): Domain ID of the scoped project if auth is
                                    project-scoped.
* ``domain_id`` (optional): domain ID of the scoped domain if auth is
                            domain-scoped
* ``domain_name`` (optional): domain name of the scoped domain if auth is
                              domain-scoped
* ``is_delegated_auth``: True if this is delegated (via trust or oauth)
* ``trust_id``: Trust ID if trust-scoped, or None
* ``trustor_id``: Trustor ID if trust-scoped, or None
* ``trustee_id``: Trustee ID if trust-scoped, or None
* ``consumer_id``: OAuth consumer ID, or None
* ``access_token_id``: OAuth access token ID, or None
* ``roles`` (optional): list of role names for the given scope
* ``group_ids`` (optional): list of group IDs for which the API user has
                            membership if token was for a federated user

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
    auth_context['user_domain_id'] = token.user_domain_id

    if token.project_scoped:
        auth_context['project_id'] = token.project_id
        auth_context['project_domain_id'] = token.project_domain_id
    elif token.domain_scoped:
        auth_context['domain_id'] = token.domain_id
        auth_context['domain_name'] = token.domain_name
    else:
        LOG.debug('RBAC: Proceeding without project or domain scope')

    if token.trust_scoped:
        auth_context['is_delegated_auth'] = True
        auth_context['trust_id'] = token.trust_id
        auth_context['trustor_id'] = token.trustor_user_id
        auth_context['trustee_id'] = token.trustee_user_id
    else:
        # NOTE(lbragstad): These variables will already be set to None but we
        # add the else statement here for readability.
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
    else:
        # NOTE(lbragstad): These variables will already be set to None but we
        # add the else statement here for readability.
        auth_context['consumer_id'] = None
        auth_context['access_token_id'] = None

    if token.is_federated_user:
        auth_context['group_ids'] = token.federation_group_ids

    return auth_context


def enforce(token_provider_api, policy_api, policy_dict, member_name,
            context, function_name, *args, **kwargs):
    action = 'identity:%s' % function_name
    creds = build_policy_check_credentials(token_provider_api, action,
                                           context, kwargs)

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
    policy_api.enforce(creds,
                       action,
                       utils.flatten_dict(policy_dict))
    LOG.debug('RBAC: Authorization granted')


def build_policy_check_credentials(
        token_provider_api, action, context, kwargs):
    kwargs_str = ', '.join(['%s=%s' % (k, kwargs[k]) for k in kwargs])
    kwargs_str = strutils.mask_password(kwargs_str)

    LOG.debug('RBAC: Authorizing %(action)s(%(kwargs)s)', {
        'action': action,
        'kwargs': kwargs_str})

    # see if auth context has already been created. If so use it.
    if ('environment' in context and
            AUTH_CONTEXT_ENV in context['environment']):
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
        validate_token_bind(context, token_ref)
    except exception.TokenNotFound:
        LOG.warning(_LW('RBAC: Invalid token'))
        raise exception.Unauthorized()

    auth_context = token_to_auth_context(token_ref)

    return auth_context


def check_protection(token_provider_api, policy_api, context, prep_info,
                     target_attr=None):
    """Provide call protection for complex target attributes.

    As well as including the standard parameters from the original API
    call (which is passed in prep_info), this call will add in any
    additional entities or attributes (passed in target_attr), so that
    they can be referenced by policy rules.

    """
    if 'is_admin' in context and context['is_admin']:
        LOG.warning(_LW('RBAC: Bypassing authorization'))
    else:
        action = 'identity:%s' % prep_info['f_name']
        # TODO(henry-nash) need to log the target attributes as well
        creds = build_policy_check_credentials(token_provider_api, action,
                                               context,
                                               prep_info['input_attr'])
        # Build the dict the policy engine will check against from both the
        # parameters passed into the call we are protecting (which was
        # stored in the prep_info by protected()), plus the target
        # attributes provided.
        policy_dict = {}
        if target_attr:
            policy_dict = {'target': target_attr}
        policy_dict.update(prep_info['input_attr'])
        if 'filter_attr' in prep_info:
            policy_dict.update(prep_info['filter_attr'])
        policy_api.enforce(creds,
                           action,
                           utils.flatten_dict(policy_dict))
        LOG.debug('RBAC: Authorization granted')


def get_token_ref(context):
    """Retrieves KeystoneToken object from the auth context and returns it.

    :param dict context: The request context.
    :raises keystone.exception.Unauthorized: If auth context cannot be found.
    :returns: The KeystoneToken object.
    """
    try:
        # Retrieve the auth context that was prepared by AuthContextMiddleware.
        auth_context = (context['environment'][AUTH_CONTEXT_ENV])
        return auth_context['token']
    except KeyError:
        LOG.warning(_LW("Couldn't find the auth context."))
        raise exception.Unauthorized()


def validate_token_bind(context, token_ref):
    bind_mode = CONF.token.enforce_token_bind

    if bind_mode == 'disabled':
        return

    if not isinstance(token_ref, token_model.KeystoneToken):
        raise exception.UnexpectedError(_('token reference must be a '
                                          'KeystoneToken type, got: %s') %
                                        type(token_ref))
    bind = token_ref.bind

    # permissive and strict modes don't require there to be a bind
    permissive = bind_mode in ('permissive', 'strict')

    if not bind:
        if permissive:
            # no bind provided and none required
            return
        else:
            LOG.info(_LI("No bind information present in token"))
            raise exception.Unauthorized()

    # get the named mode if bind_mode is not one of the known
    name = None if permissive or bind_mode == 'required' else bind_mode

    if name and name not in bind:
        LOG.info(_LI("Named bind mode %s not in bind information"), name)
        raise exception.Unauthorized()

    for bind_type, identifier in bind.items():
        if bind_type == 'kerberos':
            if not (context['environment'].get('AUTH_TYPE', '').lower()
                    == 'negotiate'):
                LOG.info(_LI("Kerberos credentials required and not present"))
                raise exception.Unauthorized()

            if not context['environment'].get('REMOTE_USER') == identifier:
                LOG.info(_LI("Kerberos credentials do not match "
                             "those in bind"))
                raise exception.Unauthorized()

            LOG.info(_LI("Kerberos bind authentication successful"))

        elif bind_mode == 'permissive':
            LOG.debug(("Ignoring unknown bind for permissive mode: "
                       "{%(bind_type)s: %(identifier)s}"),
                      {'bind_type': bind_type, 'identifier': identifier})
        else:
            LOG.info(_LI("Couldn't verify unknown bind: "
                         "{%(bind_type)s: %(identifier)s}"),
                     {'bind_type': bind_type, 'identifier': identifier})
            raise exception.Unauthorized()
