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

import base64
import hashlib
import six
import sys

from oslo_log import log
from oslo.serialization import jsonutils

from keystone import exception
from keystone.auth.controllers import AuthInfo
from keystone.common import dependency
from keystone.contrib.federation import utils
from keystone.i18n import _, _LW
from keystone.models import token_model

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


@dependency.requires('federation_api', 'identity_api', 'assignment_api')
class TokenlessAuthHelper(object):
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Make the class as a singleton class.
        """
        if not cls._instance:
            cls._instance = super(TokenlessAuthHelper, cls).__new__(
                                cls, *args, **kwargs)
        return cls._instance
    
    
    def __init__(self):
        pass

    def _build_scope_info(self, env):
        """ Build the token request scope based on the headers.

        :param env: request environment
        :return: scope data
        """
        project_id = env.get('HTTP_X_PROJECT_ID')
        project_name = env.get('HTTP_X_PROJECT_NAME')
        project_domain_id = env.get('HTTP_X_PROJECT_DOMAIN_ID')
        project_domain_name = env.get('HTTP_X_PROJECT_DOMAIN_NAME')
        domain_id = env.get('HTTP_X_DOMAIN_ID')
        domain_name = env.get('HTTP_X_DOMAIN_NAME')

        scope = {}
        if project_id or project_name:
            if project_id:
                scope['project'] = {'id': project_id}
            else:
                scope['project'] = {'name': project_name}
                if project_domain_id:
                    scope['project']['domain'] = {'id': project_domain_id}
                elif project_domain_name:
                    scope['project']['domain'] = {'name': project_domain_name}
        elif domain_id or domain_name:
            if domain_id:
                scope['domain'] = {'id': domain_id}
            else:
                scope['domain'] = {'name': domain_name}
        else:
            # must be a scoped token
            raise exception.ValidationError(
                attribute='project or domain',
                target='scope')
        return scope

    def get_scope(self, env):
        auth = {'auth': {'identity': {}}}
        # NOTE(chioleong): auth methods here is insignificant because we only care about
        # using auth.controllers.AuthInfo to validate the scope information
        auth['auth']['identity']['methods'] = ['token']
        auth['auth']['identity']['token'] = {}
        auth['auth']['scope'] = self._build_scope_info(env)

        # NOTE(chioleong): we'll let AuthInfo validate the scope for us
        auth_info = AuthInfo.create({}, auth)
        return auth_info.get_scope()
    
    def get_mapped_user(self, env):
        """Map X.509 client cert to an existing user.
        
        :param env: The environment that should contain client
            certificate attributes, such as
            SSL_CLIENT_S_DN_CN, SSL_CLIENT_I_DN_O
        :return: A dictionary that contains the keys, such as
            user_id, user_name, domain_id, domain_name
        """
        idp_id = self._build_idp_id(env)
        LOG.debug("The IDP used for looking up the x509 mapping is %s" % x509_idp)
        
        # NOTE{chioleong}: The protocol 'x509' is hard coded here. 
        # It may alternatively be a configurable option.
        mapping = self.federation_api.get_mapping_from_idp_and_protocol(
            idp_id, 'x509')
        rules = jsonutils.loads(mapping['rules'])
        LOG.debug('Tokenless authentication uses the following rules: %s', rules)
        rule_processor = utils.RuleProcessor(rules)
        mapped_properties = rule_processor.process(env)

        user_id = mapped_properties.get('user_id')
        user_name = mapped_properties.get('user_name')
        user_domain_name = mapped_properties.get('user_domain_name')
        user_domain_id = mapped_properties.get('user_domain_id')

        if user_id:
            user_ref = self.identity_api.get_user(user_id)
        elif (user_name and (user_domain_name or user_domain_id)):
            if user_domain_name:
                user_domain = self.resource_api.get_domain_by_name(domain_name)
                self.resource_api.assert_domain_enabled(user_domain['id'], user_domain)
                user_domain_id = user_domain['id']
            user_ref = self.identity_api.get_user_by_name(user_name, user_domain_id)
        else:
            msg = _LW('User auth cannot be built due to missing '
                'provided input: user Id is None or (user_name and domain_id) '
                'is None or (user_name and domain_name) is None')
            raise exception.ValidationError(msg)
        self.assert_user_is_enabled(user_ref['id'], user_ref)
        return user_ref
        
    def _build_idp_id(self, env):
        """Build the IDP name from the given attribute SSL_CLIENT_I_DN
        in the environment with the following formula -
        
        base64_idp = base64(sha1(env['SSL_CLIENT_I_DN']))
        
        :param env: The environment
        :returns: base64_idp like the above example
        """
        try:
            idp = env.get('SSL_CLIENT_I_DN')
        except KeyError as e:
            six.reraise(exception.ValidationError(e))
        
        hashed_idp = hashlib.sha256(idp)
        return base64.b64encode(hashed_idp.digest())
