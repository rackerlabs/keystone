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
import copy

from oslo_log import log
from oslo_utils import strutils

from keystone.common import utils
from keystone import exception
from keystone.i18n import _, _LW
from keystone.models import token_model


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
        auth_context['is_domain'] = token.is_domain
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

    auth_context['is_admin_project'] = token.is_admin_project
    return auth_context


def assert_admin(app, request):
    """Ensure the user is an admin.

    :raises keystone.exception.Unauthorized: if a token could not be
        found/authorized, a user is invalid, or a tenant is
        invalid/not scoped.
    :raises keystone.exception.Forbidden: if the user is not an admin and
        does not have the admin role

    """
    request.assert_authenticated()

    if not request.context.is_admin:
        user_token_ref = get_token_ref(request.context_dict)

        creds = copy.deepcopy(user_token_ref.metadata)

        try:
            creds['user_id'] = user_token_ref.user_id
        except exception.UnexpectedError:
            LOG.debug('Invalid user')
            raise exception.Unauthorized()

        if user_token_ref.project_scoped:
            creds['tenant_id'] = user_token_ref.project_id
        else:
            LOG.debug('Invalid tenant')
            raise exception.Unauthorized()

        creds['roles'] = user_token_ref.role_names
        # Accept either is_admin or the admin role
        app.policy_api.enforce(creds, 'admin_required', {})


def _build_policy_check_credentials(action, context, kwargs):
    kwargs_str = ', '.join(['%s=%s' % (k, kwargs[k]) for k in kwargs])
    kwargs_str = strutils.mask_password(kwargs_str)
    msg = 'RBAC: Authorizing %(action)s(%(kwargs)s)'
    LOG.debug(msg, {'action': action, 'kwargs': kwargs_str})

    return context['environment'].get(AUTH_CONTEXT_ENV, {})


def inner_check(self, f, callback, request, *args, **kwargs):
    request.assert_authenticated()

    if request.context.is_admin:
        LOG.warning(_LW('RBAC: Bypassing authorization'))
    elif callback is not None:
        prep_info = {'f_name': f.__name__,
                     'input_attr': kwargs}
        callback(self,
                 request,
                 prep_info,
                 *args,
                 **kwargs)
    else:
        action = 'identity:%s' % f.__name__
        creds = _build_policy_check_credentials(
            action,
            request.context_dict,
            kwargs)

        policy_dict = {}

        # Check to see if we need to include the target entity in our
        # policy checks.  We deduce this by seeing if the class has
        # specified a get_member() method and that kwargs contains the
        # appropriate entity id.
        if (hasattr(self, 'get_member_from_driver') and
                self.get_member_from_driver is not None):
            key = '%s_id' % self.member_name
            if key in kwargs:
                ref = self.get_member_from_driver(kwargs[key])
                policy_dict['target'] = {self.member_name: ref}

        # TODO(henry-nash): Move this entire code to a member
        # method inside v3 Auth
        if request.context_dict.get('subject_token_id') is not None:
            token_ref = token_model.KeystoneToken(
                token_id=request.context_dict['subject_token_id'],
                token_data=self.token_provider_api.validate_token(
                    request.context_dict['subject_token_id']))
            policy_dict.setdefault('target', {})
            policy_dict['target'].setdefault(self.member_name, {})
            policy_dict['target'][self.member_name]['user_id'] = (
                token_ref.user_id)
            try:
                user_domain_id = token_ref.user_domain_id
            except exception.UnexpectedError:
                user_domain_id = None
            if user_domain_id:
                policy_dict['target'][self.member_name].setdefault(
                    'user', {})
                policy_dict['target'][self.member_name][
                    'user'].setdefault('domain', {})
                policy_dict['target'][self.member_name]['user'][
                    'domain']['id'] = (
                        user_domain_id)

        # Add in the kwargs, which means that any entity provided as a
        # parameter for calls like create and update will be included.
        policy_dict.update(kwargs)
        self.policy_api.enforce(creds,
                                action,
                                utils.flatten_dict(policy_dict))
        LOG.debug('RBAC: Authorization granted')


def filterprotected_wrapper(self, request, filters, callback, f, **kwargs):
    request.assert_authenticated()

    if not request.context.is_admin:
        # The target dict for the policy check will include:
        #
        # - Any query filter parameters
        # - Data from the main url (which will be in the kwargs
        #   parameter), which although most of our APIs do not utilize,
        #   in theory you could have.
        #

        # First build the dict of filter parameters
        target = dict()
        if filters:
            for item in filters:
                if item in request.params:
                    target[item] = request.params[item]

            LOG.debug('RBAC: Adding query filter params (%s)', (
                ', '.join(['%s=%s' % (item, target[item])
                          for item in target])))

        if 'callback' in callback and callback['callback'] is not None:
            # A callback has been specified to load additional target
            # data, so pass it the formal url params as well as the
            # list of filters, so it can augment these and then call
            # the check_protection() method.
            prep_info = {'f_name': f.__name__,
                         'input_attr': kwargs,
                         'filter_attr': target}
            callback['callback'](self,
                                 request,
                                 prep_info,
                                 **kwargs)
        else:
            # No callback, so we are going to check the protection here
            action = 'identity:%s' % f.__name__
            creds = _build_policy_check_credentials(
                action, request.context_dict, kwargs)
            # Add in any formal url parameters
            for key in kwargs:
                target[key] = kwargs[key]

            self.policy_api.enforce(creds,
                                    action,
                                    utils.flatten_dict(target))

            LOG.debug('RBAC: Authorization granted')
    else:
        LOG.warning(_LW('RBAC: Bypassing authorization'))


def check_protection(self, request, prep_info, target_attr=None):
    """Provide call protection for complex target attributes.

    As well as including the standard parameters from the original API
    call (which is passed in prep_info), this call will add in any
    additional entities or attributes (passed in target_attr), so that
    they can be referenced by policy rules.

    """
    if request.context.is_admin:
        LOG.warning(_LW('RBAC: Bypassing authorization'))
    else:
        action = 'identity:%s' % prep_info['f_name']
        # TODO(henry-nash) need to log the target attributes as well
        creds = _build_policy_check_credentials(
            action,
            request.context_dict,
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
        self.policy_api.enforce(creds,
                                action,
                                utils.flatten_dict(policy_dict))
        LOG.debug('RBAC: Authorization granted')


def get_token_ref(context):
    """Retrieve KeystoneToken object from the auth context and returns it.

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
