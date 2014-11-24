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

from datetime import datetime

from oslo_utils import timeutils
import six

from keystone import exception
from keystone.models import core


# Access Info is version agnostic.  The builder code is version aware.
V2 = 'v2.0'
V3 = 'v3.0'
VERSIONS = frozenset([V2, V3])


def enforce_datetime(value):
    if type(value) == datetime:
        if value.tzinfo is None:
            raise ValueError('')
        return value
    elif isinstance(value, six.string_types):
        return timeutils.parse_isotime(value)
    else:
        raise ValueError('datetime from unsupported class')


class Builder(object):
    def __init__(self):
        self.user_info = None
        self.user_domain = core.Domain(None, None)
        self.methods = []
        self.roles = []
        self.scope = None
        self.services = None
        self.services_list = []
        self.federation = None
        self.audit_ids = []

        self.trust = None
        self.oauth = None
        self.service_providers = None

    def add_method(self, method):
        self.methods.append(method)

    def set_expires_at(self, expires_at):
        self.expires_at = enforce_datetime(expires_at)

    def set_issued_at(self, issued_at):
        self.issued_at = enforce_datetime(issued_at)

    def add_federation(self, federation):
        groups = []
        for group in federation['groups']:
            groups.append(core.Group(group['id']))
        self.federation = core.Federation(
            federation['identity_provider'], federation['protocol'],
            core.Groups(groups))

    def add_user_info(self, user_info):
        self.user_info = user_info

    def add_user_domain_info(self, domain_id, domain_name):
        self.user_domain = core.Domain(domain_id, domain_name)

    def add_role(self, id, name):
        role = core.Role(id, name)
        role.lock()
        self.roles.append(role)

    def add_project_scope(self, project_data):
        scope_domain_data = project_data['domain']
        scope_domain = core.Domain(
            scope_domain_data['id'],
            scope_domain_data['name'],
        )
        self.scope = core.Project(
            project_data['id'],
            project_data['name'],
            scope_domain)

    def add_domain_scope(self, domain_data):
        self.scope = core.Domain(
            domain_data['id'],
            domain_data['name'],
        )

    def add_catalog(self):
        if self.services is None:
            self.services = dict()

    def add_service(self, service_info):
        if self.services is None:
            self.services = dict()

        id = service_info['id']

        service = core.Service(
            id,
            service_info['type'],
            service_info.get('name'), [])

        # The dictionary is used for fast reference when
        # adding endpoints, but the list maintains the order
        self.services[id] = service
        self.services_list.append(service)

    def add_service_provider(self, service_provider):
        if self.service_providers is None:
            self.service_providers = []
        self.service_providers.append(
            core.ServiceProvider(
                id=service_provider['id'],
                auth_url=service_provider['auth_url'],
                sp_url=service_provider['sp_url']))

    def add_endpoint(self, service_id, endpoint_data):
        # While the spec defines that the Endpoint should have
        # both region and region_id, older servers might not
        # honor that.  Makes these values optional.
        self.services[service_id].endpoints.append(
            core.V3Endpoint(
                endpoint_data['id'],
                endpoint_data['interface'],
                endpoint_data.get('region'),
                endpoint_data.get('region_id'),
                endpoint_data['url']))

    def add_v2_endpoint(self, service_id, endpoint_data):

        self.services[service_id].endpoints.append(
            core.V2Endpoint(
                endpoint_data.get('id'),
                endpoint_data.get('tenantId'),
                endpoint_data.get('region'),
                endpoint_data.get('type'),
                endpoint_data.get('publicURL'),
                endpoint_data.get('internalURL'),
                endpoint_data.get('adminURL'),
                endpoint_data.get('versionInfo'),
                endpoint_data.get('versionList'),
                endpoint_data.get('versionId')))

    def add_v2_endpoint_old(self, service_id, endpoint_data):

        for interface in ['public', 'internal', 'admin']:
            url = interface + 'URL'
            if endpoint_data.get(url) is not None:
                self.services[service_id].endpoints.append(
                    core.V2Endpoint(
                        endpoint_data.get('id'),
                        endpoint_data.get('tenantId'),
                        endpoint_data.get('region'),
                        interface,
                        endpoint_data.get(url),
                        endpoint_data.get('versionInfo'),
                        endpoint_data.get('versionList'),
                        endpoint_data.get('versionId')))

    def add_trust(self, id, impersonation, trustor_id, trustee_id):
        self.trust = core.Trust(
            id, impersonation, trustor_id, trustee_id)

    def add_oauth(self, consumer_id, access_token_id):
        self.oauth = core.Oauth(consumer_id, access_token_id)

    def add_audit_id(self, audit_id):
        self.audit_ids.append(audit_id)

    def build(self):
        user = core.User(
            self.user_info['id'],
            self.user_info['name'],
            self.user_domain)

        if self.services is None:
            catalog = None
        else:
            # Use the list to maintain ordering
            catalog = core.Catalog(self.services_list)

        delegation = self.trust or self.oauth

        if self.service_providers is None:
            service_providers = None
        else:
            service_providers = core. ServiceProviders(self.service_providers)

        token = core.Token(user, catalog, tuple(self.roles),
                           self.expires_at, self.issued_at,
                           self.methods, self.scope, delegation,
                           self.federation, self.audit_ids,
                           service_providers)
        return token


def get_token_version(token_data):
    '''Determines the version from the deserialized token data.

    @param token_data:  the authorization data associated with a token.
    @returns the major version number of the token data from the set
    of VERSIONS

    Since early version of the tokens do not have a version field
    select the version based on the available field names.
    This logic should be deprecated In future revisions, and
    the logic should be reduced to checking the version field in
    the token_data itself. This way we can support future versions
    that might have the same fields.
    '''
    if token_data and isinstance(token_data, dict):
        if 'token_version' in token_data:
            if token_data['token_version'] in VERSIONS:
                return token_data['token_version']
        if 'access' in token_data:
            return V2
        elif 'methods' in token_data.get('token', {}):
            return V3
        else:
            raise exception.UnsupportedTokenVersionException()


class PythonDirector(object):

    def construct(self, token):
        version = get_token_version(token)
        if version == V2:
            return self.construct_core_v2(token, 'default')
        elif version == V3:
            return self.construct_core_v3(token['token'])
        else:
            # Should never reach here, as the exception would be thrown
            # by get_token_version
            raise exception.UnsupportedTokenVersionException()

    def construct_core_v3(self, token_data):
        builder = Builder()

        builder.set_expires_at(token_data['expires_at'])
        builder.set_issued_at(token_data['issued_at'])

        methods = token_data.get('methods', [])
        for method in methods:
            builder.add_method(method)

        user = token_data['user']
        builder.add_user_info(user)
        if user.get('domain') is not None:
            builder.add_user_domain_info(
                user['domain']['id'],
                user['domain']['name'])

        federation_info = user.get('OS-FEDERATION')
        if federation_info:
            builder.add_federation(federation_info)

        for role in token_data.get('roles', []):
            builder.add_role(role['id'], role['name'])

        project_data = token_data.get('project')
        if project_data:
            builder.add_project_scope(project_data)

        domain_data = token_data.get('domain')
        if domain_data:
            builder.add_domain_scope(domain_data)

        catalog_data = token_data.get('catalog')
        if catalog_data is not None:
            builder.add_catalog()
            # Fixture sending an empty dict for catalog data
            # This a work around, but should be removed when the
            # fixture is corrected
            if len(catalog_data) == 0:
                catalog_data = []
            for service in catalog_data:
                builder.add_service(service)
                for endpoint in service['endpoints']:
                    builder.add_endpoint(service['id'], endpoint)

        trust = token_data.get('OS-TRUST:trust')
        if trust is not None:
            builder.add_trust(
                trust['id'],
                trust['impersonation'],
                trust['trustor_user']['id'],
                trust['trustee_user']['id'])
        oauth1 = token_data.get('OS-OAUTH1')
        if oauth1 is not None:
            builder.add_oauth(oauth1['consumer_id'], oauth1['access_token_id'])

        for audit_id in token_data.get('audit_ids', []):
            builder.add_audit_id(audit_id)

        for service_provider in token_data.get('service_providers', []):
            builder.add_service_provider(service_provider)

        return builder.build()

    def construct_core_v2(self, token, default_domain_id):
        builder = Builder()
        # TODO(ayoung):Get this from somewhere, but where?
        DEFAULT_DOMAIN_ID = 'default'
        DEFAULT_DOMAIN_NAME = 'Default'
        DEFAULT_DOMAIN = {
            'id': DEFAULT_DOMAIN_ID,
            'name': DEFAULT_DOMAIN_NAME
        }

        token_data = token['access']['token']

        expires_at = timeutils.parse_isotime(token_data['expires'])
        issued_at = timeutils.parse_isotime(token_data['issued_at'])

        builder.set_expires_at(expires_at)
        builder.set_issued_at(issued_at)

        access = token['access']

        user = access.get('user', {})
        builder.add_user_info(user)

        builder.add_user_domain_info(DEFAULT_DOMAIN_ID, DEFAULT_DOMAIN_NAME)

        project = token_data.get('tenant')
        if project is None:
            # Fixture data only sets the tenantId
            tenant_id = user.get('tenantId')
            if tenant_id:
                project = {'id': tenant_id,
                           'name': user.get('tenantName')}
        if project is not None:
            project['domain'] = DEFAULT_DOMAIN
            builder.add_project_scope(project)

        trust = access.get('trust')
        if trust is not None:
            builder.add_trust(
                trust['id'],
                trust['impersonation'],
                trust['trustor_user_id'],
                trust['trustee_user_id'])
        # Roles are by ID in metadata and by name in the user section
        # There is no correlation between the two.  We are going to make
        # the poor assumption that they are parallel arrays.
        user_roles = access.get('user', {}).get('roles', [])
        metadata_roles = access.get('metadata', {}).get('roles', [])
        for i, user_role in enumerate(user_roles):
            role_name = user_role['name']
            try:
                role_id = metadata_roles[i]
            except IndexError:
                # There is no hard and fast rule that says the role_ids need
                # to be in the metadata.  While that is the way the server is
                # coded, many of the tests do not enforce this.  The hack is
                # to treat the name as the ID, as the ID is not really used.
                role_id = user_role['name']
            builder.add_role(role_id, role_name)

        services = access.get('serviceCatalog')
        if services is not None:
            builder.add_catalog()
            for service in services:
                service['id'] = service['name']
                # TODO(ayoung):  V2 Catalog Services don't have Ids, but V3 do.
                builder.add_service(service)
                for endpoint in service['endpoints']:
                    builder.add_v2_endpoint(service['name'], endpoint)

        for audit_id in access["token"].get("audit_ids", []):
            builder.add_audit_id(audit_id)

        return builder.build()
