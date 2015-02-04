# Copyright 2015 Hewlett-Packard
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
import sys

from oslo_config import cfg
from oslo_log import log
from oslo_serialization import jsonutils
import six

from keystone.auth import controllers
from keystone.common import dependency
from keystone.contrib import federation
from keystone.contrib.federation import utils
from keystone import exception
from keystone.i18n import _, _LW

CONF = cfg.CONF
LOG = log.getLogger(__name__)


@dependency.requires('assignment_api', 'federation_api',
                     'identity_api', 'resource_api')
class TokenlessAuthHelper(object):
    def _build_scope_info(self, env):
        """Build the token request scope based on the headers.

        :param env: request environment
        :returns: scope data
        :rtype: dict
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
                else:
                    msg = _LW('Project-domain Id or Project-domain name '
                              'is not provided.')
                    raise exception.ValidationError(msg)
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
        auth = {}
        # NOTE(chioleong): auth methods here is insignificant because
        # we only care about using auth.controllers.AuthInfo
        # to validate the scope information. Therefore,
        # we don't provide any identity here.
        auth['scope'] = self._build_scope_info(env)

        # NOTE(chioleong): we'll let AuthInfo validate the scope for us
        auth_info = controllers.AuthInfo.create({}, auth, scope_only=True)
        return auth_info.get_scope()

    def get_mapped_user(self, env, project_id=None,
                        domain_id=None, ephemeral_user=False):
        """Map client certificate to an existing user.

        :param env: The HTTP request environment that should contain
            client certificate attributes. These attributes should match
            with what the mapping defines. Or a user cannot be mapped and
            results un-authenticated. The following examples are for the
            attributes that reference to the client certificate's Subject's
            Common Name and Organization:
            SSL_CLIENT_S_DN_CN, SSL_CLIENT_S_DN_O
        :param project_id:  Project scope of the mapped user.
        :param domain_id: Domain scope of the mapped user.
        :param ephemeral_user: If this option is ``true``, the user
            referenced from the client certificate CN does not need to exist.
            A group needs to be defined in the corresponding mapping and
            this ephemeral user will have the same roles as what are assigned
            to the group. Defaults to False.
        :returns: A dictionary that contains the keys, such as
            user_id, user_name, domain_id, domain_name
        :rtype: dict
        """
        idp_id = self._build_idp_id(env)
        LOG.debug('The IdP Id %s and protocol Id %s are used to look up '
                  'the mapping.' % (idp_id, CONF.tokenless_auth.protocol))

        mapping = self.federation_api.get_mapping_from_idp_and_protocol(
            idp_id, CONF.tokenless_auth.protocol)
        rules = jsonutils.loads(mapping['rules'])

        rule_processor = utils.RuleProcessor(rules)
        mapped_properties = rule_processor.process(env)

        user = mapped_properties.get('user', {})
        user_id = user.get('user_id')
        user_name = user.get('user_name')
        user_domain_id = user.get('domain_id')
        user_domain_name = user.get('domain_name')

        user_ref = {}
        if ephemeral_user:
            group_ids = mapped_properties['group_ids']
            utils.validate_groups_in_backend(group_ids,
                                             mapping['id'],
                                             self.identity_api)
            group_ids.extend(
                utils.transform_to_group_ids(
                    mapped_properties['group_names'], mapping['id'],
                    self.identity_api, self.assignment_api))
            roles = self.assignment_api.get_roles_for_groups(group_ids,
                                                             project_id,
                                                             domain_id)
            role_names = [role['name'] for role in roles]
            user_ref['group_ids'] = list(set(group_ids))
            user_ref[federation.IDENTITY_PROVIDER] = idp_id
            user_ref[federation.PROTOCOL] = CONF.tokenless_auth.protocol
            if roles is not None:
                user_ref['roles'] = role_names
            return user_ref

        if user_id:
            user_ref = self.identity_api.get_user(user_id)
        elif user_name and (user_domain_name or user_domain_id):
            if user_domain_name:
                user_domain = self.resource_api.get_domain_by_name(
                    user_domain_name)
                self.resource_api.assert_domain_enabled(user_domain['id'],
                                                        user_domain)
                user_domain_id = user_domain['id']
            user_ref = self.identity_api.get_user_by_name(user_name,
                                                          user_domain_id)
        else:
            msg = _LW('User auth cannot be built due to missing '
                      'provided input: user Id is None or '
                      '(user_name and domain_id) '
                      'is None or (user_name and domain_name) is None')
            raise exception.ValidationError(msg)
        self._assert_user_is_enabled(user_ref)
        return user_ref

    def _build_idp_id(self, env):
        """Build the IDP name from the given config option issuer_attribute.

        The default issuer attribute SSL_CLIENT_I_DN in the environment is
        built with the following formula -

        base64_idp = base64(sha1(env['SSL_CLIENT_I_DN']))

        :param env: HTTP request environment
        :returns: base64_idp like the above example
        :rtype: str
        """
        idp = env.get(CONF.tokenless_auth.issuer_attribute)
        if idp is None:
            msg = _('Could not determine Identity Provider Id based on '
                    'env attribute %(issuer_attribute)s.')
            raise exception.ConfigurationError(msg % {
                'issuer_attribute': CONF.tokenless_auth.issuer_attribute})

        hashed_idp = hashlib.sha256(idp)
        return base64.b64encode(hashed_idp.digest())

    def _assert_user_is_enabled(self, user_ref):
        try:
            self.identity_api.assert_user_enabled(
                user_id=user_ref['id'],
                user=user_ref)
        except AssertionError as e:
            LOG.warning(_LW('User is disabled.'))
            six.reraise(exception.Unauthorized, exception.Unauthorized(e),
                        sys.exc_info()[2])
