# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack LLC
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

import uuid

from base_v2 import RestfulTestCase
from v2_tests import V2Tests


class JsonTestCase(RestfulTestCase, V2Tests):
    content_type = 'json'

    def _get_token_id(self, r):
        """Applicable only to JSON."""
        return r.body['access']['token']['id']

    def assertValidErrorResponse(self, r):
        self.assertIsNotNone(r.body.get('error'))
        self.assertValidError(r.body['error'])
        self.assertEqual(r.body['error']['code'], r.status)

    def assertValidExtension(self, extension):
        super(JsonTestCase, self).assertValidExtension(extension)

        self.assertIsNotNone(extension.get('description'))
        self.assertIsNotNone(extension.get('links'))
        self.assertTrue(len(extension.get('links')))
        for link in extension.get('links'):
            self.assertValidExtensionLink(link)

    def assertValidExtensionListResponse(self, r):
        self.assertIsNotNone(r.body.get('extensions'))
        self.assertIsNotNone(r.body['extensions'].get('values'))
        self.assertTrue(len(r.body['extensions'].get('values')))
        for extension in r.body['extensions']['values']:
            self.assertValidExtension(extension)

    def assertValidExtensionResponse(self, r):
        self.assertValidExtension(r.body.get('extension'))

    def assertValidAuthenticationResponse(self, r,
                                          require_service_catalog=False):
        self.assertIsNotNone(r.body.get('access'))
        self.assertIsNotNone(r.body['access'].get('token'))
        self.assertIsNotNone(r.body['access'].get('user'))

        # validate token
        self.assertIsNotNone(r.body['access']['token'].get('id'))
        self.assertIsNotNone(r.body['access']['token'].get('expires'))
        tenant = r.body['access']['token'].get('tenant')
        if tenant is not None:
            # validate tenant
            self.assertIsNotNone(tenant.get('id'))
            self.assertIsNotNone(tenant.get('name'))

        # validate user
        self.assertIsNotNone(r.body['access']['user'].get('id'))
        self.assertIsNotNone(r.body['access']['user'].get('name'))

        if require_service_catalog:
            # roles are only provided with a service catalog
            roles = r.body['access']['user'].get('roles')
            self.assertTrue(len(roles))
            for role in roles:
                self.assertIsNotNone(role.get('name'))

        serviceCatalog = r.body['access'].get('serviceCatalog')
        # validate service catalog
        if require_service_catalog:
            self.assertIsNotNone(serviceCatalog)
        if serviceCatalog is not None:
            self.assertTrue(isinstance(serviceCatalog, list))
            if require_service_catalog:
                self.assertTrue(len(serviceCatalog))
            for service in r.body['access']['serviceCatalog']:
                # validate service
                self.assertIsNotNone(service.get('name'))
                self.assertIsNotNone(service.get('type'))

                # services contain at least one endpoint
                self.assertIsNotNone(service.get('endpoints'))
                self.assertTrue(len(service['endpoints']))
                for endpoint in service['endpoints']:
                    # validate service endpoint
                    self.assertIsNotNone(endpoint.get('publicURL'))

    def assertValidTenantListResponse(self, r):
        self.assertIsNotNone(r.body.get('tenants'))
        self.assertTrue(len(r.body['tenants']))
        for tenant in r.body['tenants']:
            self.assertValidTenant(tenant)
            self.assertIsNotNone(tenant.get('enabled'))
            self.assertIn(tenant.get('enabled'), [True, False])

    def assertValidUserResponse(self, r):
        self.assertIsNotNone(r.body.get('user'))
        self.assertValidUser(r.body['user'])

    def assertValidTenantResponse(self, r):
        self.assertIsNotNone(r.body.get('tenant'))
        self.assertValidTenant(r.body['tenant'])

    def assertValidRoleListResponse(self, r):
        self.assertIsNotNone(r.body.get('roles'))
        self.assertTrue(len(r.body['roles']))
        for role in r.body['roles']:
            self.assertValidRole(role)

    def assertValidVersion(self, version):
        super(JsonTestCase, self).assertValidVersion(version)

        self.assertIsNotNone(version.get('links'))
        self.assertTrue(len(version.get('links')))
        for link in version.get('links'):
            self.assertIsNotNone(link.get('rel'))
            self.assertIsNotNone(link.get('href'))

        self.assertIsNotNone(version.get('media-types'))
        self.assertTrue(len(version.get('media-types')))
        for media in version.get('media-types'):
            self.assertIsNotNone(media.get('base'))
            self.assertIsNotNone(media.get('type'))

    def assertValidMultipleChoiceResponse(self, r):
        self.assertIsNotNone(r.body.get('versions'))
        self.assertIsNotNone(r.body['versions'].get('values'))
        self.assertTrue(len(r.body['versions']['values']))
        for version in r.body['versions']['values']:
            self.assertValidVersion(version)

    def assertValidVersionResponse(self, r):
        self.assertValidVersion(r.body.get('version'))

    def assertValidEndpointListResponse(self, r):
        self.assertIsNotNone(r.body.get('endpoints'))
        self.assertTrue(len(r.body['endpoints']))
        for endpoint in r.body['endpoints']:
            self.assertIsNotNone(endpoint.get('id'))
            self.assertIsNotNone(endpoint.get('name'))
            self.assertIsNotNone(endpoint.get('type'))
            self.assertIsNotNone(endpoint.get('publicURL'))
            self.assertIsNotNone(endpoint.get('internalURL'))
            self.assertIsNotNone(endpoint.get('adminURL'))

    def test_service_crud_requires_auth(self):
        """Service CRUD should 401 without an X-Auth-Token (bug 1006822)."""
        # values here don't matter because we should 401 before they're checked
        service_path = '/v2.0/OS-KSADM/services/%s' % uuid.uuid4().hex
        service_body = {
            'OS-KSADM:service': {
                'name': uuid.uuid4().hex,
                'type': uuid.uuid4().hex,
            },
        }

        r = self.admin_request(method='GET',
                               path='/v2.0/OS-KSADM/services',
                               expected_status=401)
        self.assertValidErrorResponse(r)

        r = self.admin_request(method='POST',
                               path='/v2.0/OS-KSADM/services',
                               body=service_body,
                               expected_status=401)
        self.assertValidErrorResponse(r)

        r = self.admin_request(method='GET',
                               path=service_path,
                               expected_status=401)
        self.assertValidErrorResponse(r)

        r = self.admin_request(method='DELETE',
                               path=service_path,
                               expected_status=401)
        self.assertValidErrorResponse(r)

    def test_user_role_list_requires_auth(self):
        """User role list should 401 without an X-Auth-Token (bug 1006815)."""
        # values here don't matter because we should 401 before they're checked
        path = '/v2.0/tenants/%(tenant_id)s/users/%(user_id)s/roles' % {
            'tenant_id': uuid.uuid4().hex,
            'user_id': uuid.uuid4().hex,
        }

        r = self.admin_request(path=path, expected_status=401)
        self.assertValidErrorResponse(r)

    def test_fetch_revocation_list_nonadmin_fails(self):
        self.admin_request(
            method='GET',
            path='/v2.0/tokens/revoked',
            expected_status=401)

    def test_fetch_revocation_list_admin_200(self):
        token = self.get_scoped_token()
        r = self.restful_request(
            method='GET',
            path='/v2.0/tokens/revoked',
            token=token,
            expected_status=200,
            port=self._admin_port())
        self.assertValidRevocationListResponse(r)

    def assertValidRevocationListResponse(self, response):
        self.assertIsNotNone(response.body['signed'])
