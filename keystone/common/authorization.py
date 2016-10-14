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

from oslo_log import log

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
        user_token_ref = utils.get_token_ref(request.context_dict)

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

    return context['environment'].get(authorization.AUTH_CONTEXT_ENV, {})
