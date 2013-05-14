# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Token lifecycle management interface."""


from keystone.common import dependency
from keystone.common import logging
from keystone.common import manager
from keystone import catalog
from keystone import config
from keystone import exception
from keystone import identity
from keystone import token as token_module
from keystone import trust
from keystone.openstack.common import jsonutils
from keystone.openstack.common import timeutils


CONF = config.CONF
LOG = logging.getLogger(__name__)


class V2TokenDataHelper(object):
    """V2 token data helper."""
    def __init__(self, context):
        self.identity_api = identity.Manager()
        self.catalog_api = catalog.Manager()
        self.context = context

    def _filter_domain_id(self, ref):
        """Remove domain_id since v2 calls are not domain-aware."""
        ref.pop('domain_id', None)
        return ref

    def _populate_scope(self, token_data, project_id):
        if project_id:
            project_ref = self.identity_api.get_project(
                self.context, project_id)
            token_data['token']['tenant'] = self._filter_domain_id(project_ref)

    def _populate_roles(self, token_data, user_id, project_id, metadata_ref):
        # FIXME(gyee): for V2, roles come from metadata
        roles = metadata_ref.get('roles', []) if metadata_ref else []
        #roles = self.identity_api.get_roles_for_user_and_project(
        #    self.context, user_id, project_id)
        if project_id and not roles:
            msg = _('User have no access to tenant')
            LOG.debug(msg)
            raise exception.Unauthorized(msg)
        roles_ref = []
        for role_id in roles:
            role_ref = self.identity_api.get_role(self.context, role_id)
            roles_ref.append({'id': role_ref['id'], 'name': role_ref['name']})
        token_data['user']['roles'] = roles_ref
        token_data['user']['roles_links'] = metadata_ref.get('roles_links', [])

    def _populate_user(self, token_data, user_id, project_id, metadata_ref):
        user_ref = self.identity_api.get_user(self.context,
                                              user_id)
        token_data['user'] = {'id': user_ref['id'],
                              'name': user_ref['name'],
                              'username': user_ref['name']}
        if project_id:
            self._populate_roles(token_data, user_id, project_id, metadata_ref)

    def _format_catalog(self, catalog_ref):
        """Munge catalogs from internal to output format
        Internal catalogs look like:

        {$REGION: {
            {$SERVICE: {
                $key1: $value1,
                ...
                }
            }
        }

        The legacy api wants them to look like

        [{'name': $SERVICE[name],
          'type': $SERVICE,
          'endpoints': [{
              'tenantId': $tenant_id,
              ...
              'region': $REGION,
              }],
          'endpoints_links': [],
         }]

        """
        if not catalog_ref:
            return []

        services = {}
        for region, region_ref in catalog_ref.iteritems():
            for service, service_ref in region_ref.iteritems():
                new_service_ref = services.get(service, {})
                new_service_ref['name'] = service_ref.pop('name')
                new_service_ref['type'] = service
                new_service_ref['endpoints_links'] = []
                service_ref['region'] = region

                endpoints_ref = new_service_ref.get('endpoints', [])
                endpoints_ref.append(service_ref)

                new_service_ref['endpoints'] = endpoints_ref
                services[service] = new_service_ref

        return services.values()

    def _populate_service_catalog(self, token_data, user_id, project_id,
                                  metadata_ref):
        catalog = []
        if project_id:
            catalog_ref = self.catalog_api.get_catalog(
                context=self.context,
                user_id=user_id,
                tenant_id=project_id,
                metadata=metadata_ref)
            catalog = self._format_catalog(catalog_ref)
        token_data['serviceCatalog'] = catalog

    def _populate_token(self, token_data, user_id, expires, project_id):
        if not expires:
            expires = token_module.default_expire_time()
        if not isinstance(expires, basestring):
            expires = timeutils.isotime(expires, subsecond=True)
        token_data['token'] = {'expires': expires,
                               'issued_at': timeutils.isotime(subsecond=True)}
        self._populate_scope(token_data, project_id)

    def _populate_metadata(self, token_data, metadata_ref):
        if metadata_ref:
            if 'is_admin' in metadata_ref:
                token_data['metadata'] = {'is_admin': metadata_ref['is_admin']}
            else:
                token_data['metadata'] = {'is_admin': '0'}
            # FIXME(gyee): why are we stashing roles in metadata_ref?
            if 'roles' in metadata_ref:
                token_data['metadata']['roles'] = metadata_ref['roles']

    def _populate_trust(self, token_data, metadata_ref):
        if metadata_ref and CONF.trust.enabled and 'trust_id' in metadata_ref:
            token_data['trust'] = {'trustee_user_id':
                                   metadata_ref['trustee_user_id'],
                                   'id': metadata_ref['trust_id']
                                   }

    def get_token_data(self, user_id, expires=None,
                       project_id=None, metadata_ref=None):
        token_data = {}
        self._populate_user(token_data, user_id, project_id, metadata_ref)
        self._populate_token(token_data, user_id, expires, project_id)
        self._populate_service_catalog(token_data, user_id, project_id,
                                       metadata_ref)
        self._populate_metadata(token_data, metadata_ref)
        self._populate_trust(token_data, metadata_ref)
        return {'access': token_data}


class TokenDataHelper(object):
    """Token data helper."""
    def __init__(self, context):
        self.identity_api = identity.Manager()
        self.catalog_api = catalog.Manager()
        self.context = context

    def _get_filtered_domain(self, domain_id):
        domain_ref = self.identity_api.get_domain(self.context,
                                                  domain_id)
        return {'id': domain_ref['id'], 'name': domain_ref['name']}

    def _populate_scope(self, token_data, domain_id, project_id):
        if domain_id:
            token_data['domain'] = self._get_filtered_domain(domain_id)
        if project_id:
            project_ref = self.identity_api.get_project(
                self.context, project_id)
            filtered_project = {
                'id': project_ref['id'],
                'name': project_ref['name']}
            filtered_project['domain'] = self._get_filtered_domain(
                project_ref['domain_id'])
            token_data['project'] = filtered_project

    def _get_project_roles_for_user(self, user_id, project_id):
        roles = self.identity_api.get_roles_for_user_and_project(
            self.context, user_id, project_id)
        roles_ref = []
        for role_id in roles:
            role_ref = self.identity_api.get_role(self.context, role_id)
            role_ref.setdefault('project_id', project_id)
            roles_ref.append(role_ref)
        # user have no project roles, therefore access denied
        if not roles_ref:
            msg = _('User have no access to project')
            LOG.debug(msg)
            raise exception.Unauthorized(msg)
        return roles_ref

    def _get_domain_roles_for_user(self, user_id, domain_id):
        roles = self.identity_api.get_roles_for_user_and_domain(
            self.context, user_id, domain_id)
        roles_ref = []
        for role_id in roles:
            role_ref = self.identity_api.get_role(self.context, role_id)
            role_ref.setdefault('domain_id', domain_id)
            roles_ref.append(role_ref)
        # user have no domain roles, therefore access denied
        if not roles_ref:
            msg = _('User have no access to domain')
            LOG.debug(msg)
            raise exception.Unauthorized(msg)
        return roles_ref

    def _get_roles_for_user(self, user_id, domain_id, project_id):
        roles = []
        if domain_id:
            roles = self._get_domain_roles_for_user(user_id, domain_id)
        if project_id:
            roles = self._get_project_roles_for_user(user_id, project_id)
        return roles

    def _populate_user(self, token_data, user_id, domain_id, project_id,
                       trust):
        user_ref = self.identity_api.get_user(self.context,
                                              user_id)
        if CONF.trust.enabled and trust:
            trustor_user_ref = (self.identity_api.get_user(self.context,
                                trust['trustor_user_id']))
            if not trustor_user_ref['enabled']:
                raise exception.Forbidden()
            if trust['impersonation']:
                user_ref = trustor_user_ref
            token_data['OS-TRUST:trust'] = (
                {
                    'id': trust['id'],
                    'trustor_user': {'id': trust['trustor_user_id']},
                    'trustee_user': {'id': trust['trustee_user_id']},
                    'impersonation': trust['impersonation']
                })
        filtered_user = {
            'id': user_ref['id'],
            'name': user_ref['name'],
            'domain': self._get_filtered_domain(user_ref['domain_id'])}
        token_data['user'] = filtered_user

    def _populate_roles(self, token_data, user_id, domain_id, project_id,
                        trust):
        if CONF.trust.enabled and trust:
            token_user_id = trust['trustor_user_id']
            token_project_id = trust['project_id']
            #trusts do not support domains yet
            token_domain_id = None
        else:
            token_user_id = user_id
            token_project_id = project_id
            token_domain_id = domain_id

        if token_domain_id or token_project_id:
            roles = self._get_roles_for_user(token_user_id,
                                             token_domain_id,
                                             token_project_id)
            filtered_roles = []
            if CONF.trust.enabled and trust:
                for trust_role in trust['roles']:
                    match_roles = [x for x in roles
                                   if x['id'] == trust_role['id']]
                    if match_roles:
                        filtered_roles.append(match_roles[0])
                    else:
                        raise exception.Forbidden()
            else:
                for role in roles:
                    filtered_roles.append({'id': role['id'],
                                           'name': role['name']})
            token_data['roles'] = filtered_roles

    def _populate_service_catalog(self, token_data, user_id,
                                  domain_id, project_id, trust):
        if CONF.trust.enabled and trust:
            user_id = trust['trustor_user_id']
        if project_id or domain_id:
            try:
                service_catalog = self.catalog_api.get_v3_catalog(
                    self.context, user_id, project_id)
            #TODO KVS backend needs a sample implementation
            except exception.NotImplemented:
                service_catalog = {}
            # TODO(gyee): v3 service catalog is not quite completed yet
            #TODO Enforce Endpoints for trust
            token_data['catalog'] = service_catalog

    def _populate_token(self, token_data, expires=None, trust=None):
        if not expires:
            expires = token_module.default_expire_time()
        if not isinstance(expires, basestring):
            expires = timeutils.isotime(expires, subsecond=True)
        token_data['expires_at'] = expires
        token_data['issued_at'] = timeutils.isotime(subsecond=True)

    def get_token_data(self, user_id, method_names, extras,
                       domain_id=None, project_id=None, expires=None,
                       trust=None, need_catalog=True):
        token_data = {'methods': method_names,
                      'extras': extras}

        if CONF.trust.enabled and trust:
            if user_id != trust['trustee_user_id']:
                raise exception.Forbidden()
        self._populate_scope(token_data, domain_id, project_id)
        self._populate_user(token_data, user_id, domain_id, project_id, trust)
        self._populate_roles(token_data, user_id, domain_id, project_id, trust)
        if need_catalog:
            self._populate_service_catalog(token_data, user_id, domain_id,
                                           project_id, trust)
        self._populate_token(token_data, expires, trust)
        return {'token': token_data}


@dependency.provider('token_management_api')
class Manager(manager.Manager):
    """Default pivot point for the Token Factory provider backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """

    def __init__(self):
        super(Manager, self).__init__(CONF.token_management.driver)


class Driver(object):
    """Interface description for a Token driver."""

    def issue_v2_token(self, user_id, projec_id=None, **kwargs):
        """Issue a V2 token.

        :param user_id: identity of the user
        :type user_id: string
        :param project_id: identity of the scoped project
        :type project_id: string
        :param kwargs: other information to assist token creation
        :type kwargs: free from keyword arguments
        :returns: (token_id, token_data)
        :raises: keystone.exception.TokenNotFound

        """
        raise exception.NotImplemented()

    def issue_v3_token(self, user_id, method_names, expires_at=None,
                       project_id=None, domain_id=None, trust=None,
                       auth_context=None, **kwargs):
        """Issue a V3 token.

        :param user_id: identity of the user
        :type user_id: string
        :param method_names: authentication method names
        :type methods: list of strings
        :param expires_at: token expiration
        :type: date
        :param project_id: identity of the scoped project
        :type project_id: string
        :param domain_id: identity of the scoped domain
        :type domain_id: string
        :param trust: trust reference
        :type trust: trust reference
        :param auth_context: authentication context
        :type auth_context: dict
        :param kwargs: other information to assist token creation
        :type kwargs: free from keyword arguments
        :returns: (token_id, token_data)
        :raises: keystone.exception.TokenNotFound

        """
        raise exception.NotImplemented()

    def revoke_token(self, token_id):
        """Revoke a given token.

        :param token_id: identity of the token
        :type token_id: string
        :returns: None.
        :raises: keystone.exception.TokenNotFound
        """
        raise exception.NotImplemented()

    def validate_v2_token(self, token_id, belongs_to=None):
        """Validate the given V2 token.

        :param token_id: identity of the token
        :type token_id: string
        :param belongs_to: identity of the scoped project to validate
        :type string
        :returns: token data
        :raises: keystone.exception.TokenNotFound

        """
        raise exception.NotImplemented()

    def validate_v3_token(self, token_id, belongs_to=None, need_catalog=True):
        """Validate the given V3 token.

        :param token_id: identity of the token
        :type token_id: string
        :param belongs_to: identity of the scoped project to validate
        :type string
        :param need_catalog: indicate whether to return the service catalog
        :type boolean
        :returns: token data
        :raises: keystone.exception.TokenNotFound

        """
        raise exception.NotImplemented()

    def check_v2_token(self, token_id, belongs_to=None):
        """Check the validity of the given V2 token.

        :param token_id: identity of the token
        :type token_id: string
        :param belongs_to: identity of the scoped project to validate
        :type string
        :returns: None
        :raises: keystone.exception.TokenNotFound

        """

    def check_v3_token(self, token_id, belongs_to=None):
        """Check the validity of the given V3 token.

        :param token_id: identity of the token
        :type token_id: string
        :param belongs_to: identity of the scoped project to validate
        :type string
        :returns: None
        :raises: keystone.exception.TokenNotFound

        """
