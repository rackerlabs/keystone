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
from keystone import config
from keystone import exception
from keystone import token
from keystone import trust
from keystone.openstack.common import timeutils


CONF = config.CONF
LOG = logging.getLogger(__name__)


V2 = '2.0'
V3 = '3.0'


def get_token_version(token_data):
    """Determine the token version.

    :returns: '2.0' for V2 token or '3.0' for V3 token
    """
    if 'access' in token_data:
        return V2
    if 'token' in token_data and 'methods' in token_data['token']:
        return V3


def v3_to_v2_catalog(v3_catalog):
    service_catalog = {}
    for service_endpoints in v3_catalog:
        service_type = service_endpoints['type']
        for endpoint in service_endpoints['endpoints']:
            region = endpoint['region']
            if service_type not in service_catalog:
                service_catalog[service_type] = {
                    'id': service_endpoints['id'],
                    'name': service_endpoints['name'],
                    'type': service_type,
                    'regions': {}}
            if region not in service_catalog[service_type]['regions']:
                service_catalog[service_type]['regions'][region] = \
                    {'region': region}
            interface = '%sURL' % endpoint['interface']
            service_catalog[service_type]['regions'][region].setdefault(
                'id', endpoint['id'])
            service_catalog[service_type]['regions'][region][interface] =\
                endpoint['url']
    catalog = []
    for service_type in service_catalog:
        service_endpoints = {'name': service_catalog[service_type]['name'],
                             'type': service_catalog[service_type]['type'],
                             'endpoints_links': []}
        endpoints = []
        for region in service_catalog[service_type]['regions']:
            endpoints.append(service_catalog[service_type]['regions'][region])
        service_endpoints['endpoints'] = endpoints
        catalog.append(service_endpoints)
    return catalog


def v3_to_v2_token(token_data):
    v3_token = token_data['token']
    roles = []
    if 'roles' in v3_token:
        for role in v3_token['roles']:
            roles.append({'name': role['name']})
    o = {'access': {'token': {'id': v3_token['id'],
                              'expires': v3_token['expires_at'],
                              'issued_at': v3_token['issued_at']
                              },
                    'user': {'id': v3_token['user']['id'],
                             'name': v3_token['user']['name'],
                             'username': v3_token['user']['name'],
                             'roles': roles,
                             'roles_links': []
                             }
                    }
         }
    if 'project' in v3_token:
            o['access']['token']['tenant'] = {
                'id': v3_token['project']['id'],
                'name': v3_token['project']['name'],
                'enabled': True}
    if 'catalog' in v3_token:
            o['access']['serviceCatalog'] = v3_to_v2_catalog(
                v3_token['catalog'])
    if 'metadata' in v3_token:
        o['access']['metadata'] = v3_token['metadata']

    #FIXME(gyee): should v2 be 'OS-TRUST:trust' as well?
    if 'OS-TRUST:trust' in v3_token:
        o['access']['trust'] = {'id': v3_token['OS-TRUST:trust']['id']}
        if 'trustee_user_id' in v3_token['OS-TRUST:trust']:
            o['access']['trust']['trustee_user_id'] = \
                v3_token['OS-TRUST:trust']['trustee_user_id']
        elif 'trustee_user' in v3_token['OS-TRUST:trust']:
            o['access']['trust']['trustee_user_id'] = \
                v3_token['OS-TRUST:trust']['trustee_user']['id']
        else:
            raise exception.ValidationError(attribute='trustee_user_id',
                                            target='v3 token')
    return o


@dependency.requires('catalog_api', 'identity_api')
class TokenDataHelper(object):
    """Token data helper."""
    def __init__(self, context):
        self.context = context
        if CONF.trust.enabled:
            self.trust_api = trust.Manager()

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

    def _get_metadata_ref(self, context, user_id=None, tenant_id=None,
                          domain_id=None, group_id=None):
        """Returns metadata_ref for a user or group in a tenant or domain"""

        metadata_ref = {}
        if (user_id or group_id) and (tenant_id or domain_id):
            try:
                metadata_ref = self.identity_api.get_metadata(
                    context=context, user_id=user_id, tenant_id=tenant_id,
                    domain_id=domain_id, group_id=group_id)
            except exception.MetadataNotFound:
                pass
        return metadata_ref

    def _get_group_metadata_ref(self, context, user_id,
                                tenant_id=None, domain_id=None):
        """Return any metadata for this project/domain due to group grants"""
        group_refs = self.identity_api.list_groups_for_user(context=context,
                                                            user_id=user_id)
        metadata_ref = {}
        for x in group_refs:
            metadata_ref.update(self._get_metadata_ref(context,
                                                       group_id=x['id'],
                                                       tenant_id=tenant_id,
                                                       domain_id=domain_id))
        return metadata_ref

    def _append_roles(self, metadata, additional_metadata):
        """
        Update the roles in metadata to be the union of the roles from
        both of the passed metadatas
        """

        first = set(metadata.get('roles', []))
        second = set(additional_metadata.get('roles', []))
        metadata['roles'] = list(first.union(second))

    def _get_project_roles_for_user(self, user_id, project_id):
        #FIXME(gyee) get_roles_for_user_and_project is supposed to return
        # all the roles assigned to the user for the project, including
        # assignment via group membership. Unfortunately, not all backends
        # does this correctly. For now, lets do this explicitly.
        #roles = self.identity_api.get_roles_for_user_and_project(
        #    self.context, user_id, project_id)
        metadata_ref = self._get_metadata_ref(self.context,
                                              user_id, project_id)
        self._append_roles(metadata_ref,
                           self._get_group_metadata_ref(
                               self.context, user_id, project_id))
        roles_ref = []
        for role_id in metadata_ref.get('roles', []):
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
        #FIXME(gyee) get_roles_for_user_and_project is supposed to return
        # all the roles assigned to the user for the project, including
        # assignment via group membership. Unfortunately, not all backends
        # does this correctly. For now, lets do this explicitly.
        #roles = self.identity_api.get_roles_for_user_and_domain(
        #    self.context, user_id, domain_id)
        metadata_ref = self._get_metadata_ref(self.context,
                                              user_id, domain_id=domain_id)
        self._append_roles(metadata_ref,
                           self._get_group_metadata_ref(
                               self.context, user_id, domain_id=domain_id))
        roles_ref = []
        for role_id in metadata_ref.get('roles', []):
            role_ref = self.identity_api.get_role(self.context, role_id)
            role_ref.setdefault('domain_id', domain_id)
            roles_ref.append(role_ref)
        # user have no domain roles, therefore access denied
        if not roles_ref:
            msg = _('User have no access to domain')
            LOG.debug(msg)
            raise exception.Unauthorized(msg)
        return roles_ref

    def _get_roles_for_user(self, user_id, domain_id, project_id,
                            metadata_ref):
        roles = []
        if metadata_ref and 'roles' in metadata_ref:
            # FIXME(gyee): for V2, roles come from metadata?
            for role_id in metadata_ref.get('roles', []):
                role_ref = self.identity_api.get_role(self.context, role_id)
                roles.append({
                    'id': role_ref['id'],
                    'name': role_ref['name']})
            if project_id and not roles:
                msg = _('User have no access to tenant')
                LOG.debug(msg)
                raise exception.Unauthorized(msg)
        else:
            if domain_id:
                roles = self._get_domain_roles_for_user(user_id, domain_id)
            if project_id:
                roles = self._get_project_roles_for_user(user_id, project_id)
        return roles

    def _to_boolean(self, obj):
        if isinstance(obj, basestring):
            return obj.lower() in ('true', 't', '1')
        else:
            return obj

    def _populate_user(self, token_data, user_id, domain_id, project_id,
                       trust):
        user_ref = self.identity_api.get_user(self.context,
                                              user_id)
        if CONF.trust.enabled and trust:
            trust = self.trust_api.get_trust(self.context, trust['id'])
            trustor_user_ref = (self.identity_api.get_user(self.context,
                                trust['trustor_user_id']))
            if not trustor_user_ref['enabled']:
                raise exception.Forbidden()
            if self._to_boolean(trust['impersonation']):
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
                        metadata_ref, trust):
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
                                             token_project_id,
                                             metadata_ref)
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

    def _get_catalog(self, user_id, project_id):
        catalog_ref = self.catalog_api.get_catalog(
            context=self.context,
            user_id=user_id,
            tenant_id=project_id)
        if not catalog_ref:
            return []
        services = {}
        for region, region_ref in catalog_ref.iteritems():
            for service, service_ref in region_ref.iteritems():
                new_service_ref = services.get(service, {})
                new_service_ref.setdefault('id', service_ref['id'])
                new_service_ref.setdefault('type', service)
                new_service_ref.setdefault('name', service_ref['name'])
                if 'endpoints' not in new_service_ref:
                    new_service_ref['endpoints'] = []
                for attr in service_ref.keys():
                    if attr.endswith('URL'):
                        interface = attr[:-3]
                        new_service_ref['endpoints'].append({
                            'interface': interface,
                            'url': service_ref[attr],
                            'region': region,
                            'id': service_ref['id']})
                services[service] = new_service_ref
        return services.values()

    def _populate_service_catalog(self, token_data, user_id,
                                  domain_id, project_id, trust):
        if CONF.trust.enabled and trust:
            user_id = trust['trustor_user_id']
        if project_id or domain_id:
            try:
                service_catalog = self.catalog_api.get_v3_catalog(
                    self.context, user_id, project_id)
            except exception.NotImplemented:
                # for backends which doesn't provide v3 catalog, lets do
                # this the old way
                try:
                    service_catalog = self._get_catalog(user_id, project_id)
                except Exception as e:
                    # not much we can do here
                    LOG.exception(e)
                    service_catalog = {}
            # TODO(gyee): v3 service catalog is not quite completed yet
            #TODO Enforce Endpoints for trust
            token_data['catalog'] = service_catalog

    def _populate_token(self, token_data, expires=None, trust=None):
        if not expires:
            expires = token.default_expire_time()
        if not isinstance(expires, basestring):
            expires = timeutils.isotime(expires, subsecond=True)
        token_data['expires_at'] = expires
        token_data['issued_at'] = timeutils.isotime(subsecond=True)

    def _populate_metadata(self, token_data, metadata_ref):
        if metadata_ref:
            if 'is_admin' in metadata_ref:
                token_data['metadata'] = {'is_admin': metadata_ref['is_admin']}
            else:
                token_data['metadata'] = {'is_admin': '0'}
            # FIXME(gyee): why are we stashing roles in metadata_ref?
            if 'roles' in metadata_ref:
                token_data['metadata']['roles'] = metadata_ref['roles']

    def get_token_data(self, user_id, method_names, extras,
                       domain_id=None, project_id=None, expires=None,
                       metadata_ref=None, trust=None, need_catalog=True):
        token_data = {'methods': method_names,
                      'extras': extras}

        if CONF.trust.enabled and trust:
            if user_id != trust['trustee_user_id']:
                raise exception.Forbidden()
        self._populate_scope(token_data, domain_id, project_id)
        self._populate_user(token_data, user_id, domain_id, project_id, trust)
        self._populate_metadata(token_data, metadata_ref)
        self._populate_roles(token_data, user_id, domain_id, project_id,
                             metadata_ref, trust)
        self._populate_service_catalog(token_data, user_id, domain_id,
                                       project_id, trust)
        self._populate_token(token_data, expires, trust)
        return {'token': token_data}


@dependency.provider('token_provider_api')
class Manager(manager.Manager):
    """Default pivot point for the Token Factory provider backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """

    def __init__(self):
        # FIXME(gyee): devstack is still teeing off on token_format so we
        # need this hack to make it happy for now.
        # Will need to remove this hack once we fix devstack.
        PKI_TOKEN_PROVIDER = 'keystone.token.providers.pki_token.Provider'
        UUID_TOKEN_PROVIDER = 'keystone.token.providers.uuid_token.Provider'
        if CONF.signing.token_format == 'PKI':
            super(Manager, self).__init__(PKI_TOKEN_PROVIDER)
        elif CONF.signing.token_format == 'UUID':
            super(Manager, self).__init__(UUID_TOKEN_PROVIDER)
        else:
            super(Manager, self).__init__(CONF.token.provider)

        #super(Manager, self).__init__(CONF.token.provider)


class Driver(object):
    """Interface description for a Token provider."""

    def issue_token(self, user_id, method_names, expires_at=None,
                    project_id=None, domain_id=None,
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

    def validate_token(self, token_id, belongs_to=None,
                       belongs_to_domain=None, no_domain_scope=False,
                       **kwargs):
        """Validate the given token.

        :param token_id: identity of the token
        :type token_id: string
        :param belongs_to: identity of the scoped project to validate
        :type belongs_to: string
        :param need_catalog: indicate whether to return the service catalog
        :type need_catalog: boolean
        :param belongs_to_domain: identity of the domain in which the token
                                  is valid
        :param belongs_to_domain: string
        :param no_domain_scope: indicate whether domain scoping is allowed
        :type no_domain_scope: boolean
        :param kwargs: other information to assist token validation
        :type kwargs: free from keyword arguments
        :returns: token data
        :raises: keystone.exception.TokenNotFound

        """
        raise exception.NotImplemented()

    def check_token(self, token_id, belongs_to=None,
                    belongs_to_domain=None, no_domain_scope=False,
                    **kwargs):
        """Check the validity of the given V3 token.

        :param token_id: identity of the token
        :type token_id: string
        :param belongs_to: identity of the scoped project to validate
        :type belongs_to: string
        :param belongs_to_domain: identity of the domain in which the token
                                  is valid
        :param belongs_to_domain: string
        :param no_domain_scope: indicate whether domain scoping is allowed
        :type no_domain_scope: boolean
        :param kwargs: other information to assist token validation
        :type kwargs: free from keyword arguments
        :returns: None
        :raises: keystone.exception.TokenNotFound

        """
