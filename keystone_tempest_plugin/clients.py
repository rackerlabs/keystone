# Copyright 2016 Red Hat, Inc.
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


from tempest import clients
from tempest.common import credentials_factory as common_creds
from tempest import config
from tempest import exceptions

from tempest.lib.services.identity.v2.token_client import TokenClient
from tempest.lib.services.identity.v3.token_client import V3TokenClient

from keystone_tempest_plugin.services.identity.v2.json.endpoints_client \
    import EndpointsClient
from keystone_tempest_plugin.services.identity.v2.json.identity_client import \
    IdentityClient
from keystone_tempest_plugin.services.identity.v2.json.roles_client import \
    RolesClient
from keystone_tempest_plugin.services.identity.v2.json.services_client import \
    ServicesClient as IdentityServicesClient
from keystone_tempest_plugin.services.identity.v2.json.tenants_client import \
    TenantsClient
from keystone_tempest_plugin.services.identity.v2.json.users_client import \
    UsersClient
from keystone_tempest_plugin.services.identity.v3.json.credentials_client \
    import CredentialsClient
from keystone_tempest_plugin.services.identity.v3.json.domains_client import \
    DomainsClient
from keystone_tempest_plugin.services.identity.v3.json.endpoints_client \
    import EndPointsClient as EndPointsV3Client
from keystone_tempest_plugin.services.identity.v3.json.groups_client import \
    GroupsClient
from keystone_tempest_plugin.services.identity.v3.json.identity_client import \
    IdentityClient as IdentityV3Client
from keystone_tempest_plugin.services.identity.v3.json.policies_client import \
    PoliciesClient
from keystone_tempest_plugin.services.identity.v3.json.projects_client import \
    ProjectsClient
from keystone_tempest_plugin.services.identity.v3.json.regions_client import \
    RegionsClient
from keystone_tempest_plugin.services.identity.v3.json.roles_client import \
    RolesClient as RolesV3Client
from keystone_tempest_plugin.services.identity.v3.json.services_client import \
    ServicesClient as IdentityServicesV3Client
from keystone_tempest_plugin.services.identity.v3.json.trusts_client import \
    TrustsClient
from keystone_tempest_plugin.services.identity.v3.json.users_clients import \
    UsersClient as UsersV3Client


CONF = config.CONF

ADMIN_CREDS = common_creds.get_configured_credentials('identity_admin')


class Manager(clients.Manager):
    def __init__(self,
                 credentials=ADMIN_CREDS,
                 service=None,
                 api_microversions=None):
        super(Manager, self).__init__(credentials, service)
        self._set_identity_clients()

    def _set_identity_clients(self):
        params = {
            'service': CONF.identity.catalog_type,
            'region': CONF.identity.region
        }
        params.update(self.default_params_with_timeout_values)

        # Clients below use the admin endpoint type of Keystone API v2
        params_v2_admin = params.copy()
        params_v2_admin['endpoint_type'] = CONF.identity.v2_admin_endpoint_type
        self.endpoints_client = EndpointsClient(self.auth_provider,
                                                **params_v2_admin)
        self.identity_client = IdentityClient(self.auth_provider,
                                              **params_v2_admin)
        self.tenants_client = TenantsClient(self.auth_provider,
                                            **params_v2_admin)
        self.roles_client = RolesClient(self.auth_provider, **params_v2_admin)
        self.users_client = UsersClient(self.auth_provider, **params_v2_admin)
        self.identity_services_client = IdentityServicesClient(
            self.auth_provider, **params_v2_admin)

        # Clients below use the public endpoint type of Keystone API v2
        params_v2_public = params.copy()
        params_v2_public['endpoint_type'] = (
            CONF.identity.v2_public_endpoint_type)
        self.identity_public_client = IdentityClient(self.auth_provider,
                                                     **params_v2_public)
        self.tenants_public_client = TenantsClient(self.auth_provider,
                                                   **params_v2_public)
        self.users_public_client = UsersClient(self.auth_provider,
                                               **params_v2_public)

        # Clients below use the endpoint type of Keystone API v3
        params_v3 = params.copy()
        params_v3['endpoint_type'] = CONF.identity.v3_endpoint_type
        self.domains_client = DomainsClient(self.auth_provider,
                                            **params_v3)
        self.identity_v3_client = IdentityV3Client(self.auth_provider,
                                                   **params_v3)
        self.trusts_client = TrustsClient(self.auth_provider, **params_v3)
        self.users_v3_client = UsersV3Client(self.auth_provider, **params_v3)
        self.endpoints_v3_client = EndPointsV3Client(self.auth_provider,
                                                     **params_v3)
        self.roles_v3_client = RolesV3Client(self.auth_provider, **params_v3)
        self.identity_services_v3_client = IdentityServicesV3Client(
            self.auth_provider, **params_v3)
        self.policies_client = PoliciesClient(self.auth_provider, **params_v3)
        self.projects_client = ProjectsClient(self.auth_provider, **params_v3)
        self.regions_client = RegionsClient(self.auth_provider, **params_v3)
        self.credentials_client = CredentialsClient(self.auth_provider,
                                                    **params_v3)
        self.groups_client = GroupsClient(self.auth_provider, **params_v3)

        # Token clients do not use the catalog. They only need default_params.
        # They read auth_url, so they should only be set if the corresponding
        # API version is marked as enabled
        if CONF.identity_feature_enabled.api_v2:
            if CONF.identity.uri:
                self.token_client = TokenClient(
                    CONF.identity.uri, **self.default_params)
            else:
                msg = 'Identity v2 API enabled, but no identity.uri set'
                raise exceptions.InvalidConfiguration(msg)
        if CONF.identity_feature_enabled.api_v3:
            if CONF.identity.uri_v3:
                self.token_v3_client = V3TokenClient(
                    CONF.identity.uri_v3, **self.default_params)
            else:
                msg = 'Identity v3 API enabled, but no identity.uri_v3 set'
                raise exceptions.InvalidConfiguration(msg)
