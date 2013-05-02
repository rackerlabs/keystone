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

from base_v2 import RestfulTestCase
from v2_tests import V2ApiTests


class XmlTestCase(RestfulTestCase, V2ApiTests):
    xmlns = 'http://docs.openstack.org/identity/api/v2.0'
    content_type = 'xml'

    def _get_token_id(self, r):
        return r.result.find(self._tag('token')).get('id')

    def _tag(self, tag_name, xmlns=None):
        """Helper method to build an namespaced element name."""
        return '{%(ns)s}%(tag)s' % {'ns': xmlns or self.xmlns, 'tag': tag_name}

    def assertValidErrorResponse(self, r):
        xml = r.result
        self.assertEqual(xml.tag, self._tag('error'))

        self.assertValidError(xml)
        self.assertEqual(xml.get('code'), str(r.status_code))

    def assertValidExtension(self, extension):
        super(XmlTestCase, self).assertValidExtension(extension)

        self.assertIsNotNone(extension.find(self._tag('description')))
        self.assertTrue(extension.find(self._tag('description')).text)
        links = extension.find(self._tag('links'))
        self.assertTrue(len(links.findall(self._tag('link'))))
        for link in links.findall(self._tag('link')):
            self.assertValidExtensionLink(link)

    def assertValidExtensionListResponse(self, r):
        xml = r.result
        self.assertEqual(xml.tag, self._tag('extensions'))

        self.assertTrue(len(xml.findall(self._tag('extension'))))
        for extension in xml.findall(self._tag('extension')):
            self.assertValidExtension(extension)

    def assertValidExtensionResponse(self, r):
        xml = r.result
        self.assertEqual(xml.tag, self._tag('extension'))

        self.assertValidExtension(xml)

    def assertValidVersion(self, version):
        super(XmlTestCase, self).assertValidVersion(version)

        links = version.find(self._tag('links'))
        self.assertIsNotNone(links)
        self.assertTrue(len(links.findall(self._tag('link'))))
        for link in links.findall(self._tag('link')):
            self.assertIsNotNone(link.get('rel'))
            self.assertIsNotNone(link.get('href'))

        media_types = version.find(self._tag('media-types'))
        self.assertIsNotNone(media_types)
        self.assertTrue(len(media_types.findall(self._tag('media-type'))))
        for media in media_types.findall(self._tag('media-type')):
            self.assertIsNotNone(media.get('base'))
            self.assertIsNotNone(media.get('type'))

    def assertValidMultipleChoiceResponse(self, r):
        xml = r.result
        self.assertEqual(xml.tag, self._tag('versions'))

        self.assertTrue(len(xml.findall(self._tag('version'))))
        for version in xml.findall(self._tag('version')):
            self.assertValidVersion(version)

    def assertValidVersionResponse(self, r):
        xml = r.result
        self.assertEqual(xml.tag, self._tag('version'))

        self.assertValidVersion(xml)

    def assertValidEndpointListResponse(self, r):
        xml = r.result
        self.assertEqual(xml.tag, self._tag('endpoints'))

        self.assertTrue(len(xml.findall(self._tag('endpoint'))))
        for endpoint in xml.findall(self._tag('endpoint')):
            self.assertIsNotNone(endpoint.get('id'))
            self.assertIsNotNone(endpoint.get('name'))
            self.assertIsNotNone(endpoint.get('type'))
            self.assertIsNotNone(endpoint.get('publicURL'))
            self.assertIsNotNone(endpoint.get('internalURL'))
            self.assertIsNotNone(endpoint.get('adminURL'))

    def assertValidTenantResponse(self, r):
        xml = r.result
        self.assertEqual(xml.tag, self._tag('tenant'))

        self.assertValidTenant(xml)

    def assertValidUserResponse(self, r):
        xml = r.result
        self.assertEqual(xml.tag, self._tag('user'))

        self.assertValidUser(xml)

    def assertValidRoleListResponse(self, r):
        xml = r.result
        self.assertEqual(xml.tag, self._tag('roles'))

        self.assertTrue(len(r.result.findall(self._tag('role'))))
        for role in r.result.findall(self._tag('role')):
            self.assertValidRole(role)

    def assertValidAuthenticationResponse(self, r,
                                          require_service_catalog=False):
        xml = r.result
        self.assertEqual(xml.tag, self._tag('access'))

        # validate token
        token = xml.find(self._tag('token'))
        self.assertIsNotNone(token)
        self.assertIsNotNone(token.get('id'))
        self.assertIsNotNone(token.get('expires'))
        tenant = token.find(self._tag('tenant'))
        if tenant is not None:
            # validate tenant
            self.assertValidTenant(tenant)
            self.assertIn(tenant.get('enabled'), ['true', 'false'])

        user = xml.find(self._tag('user'))
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.get('id'))
        self.assertIsNotNone(user.get('name'))

        if require_service_catalog:
            # roles are only provided with a service catalog
            roles = user.findall(self._tag('role'))
            self.assertTrue(len(roles))
            for role in roles:
                self.assertIsNotNone(role.get('name'))

        serviceCatalog = xml.find(self._tag('serviceCatalog'))
        # validate the serviceCatalog
        if require_service_catalog:
            self.assertIsNotNone(serviceCatalog)
        if serviceCatalog is not None:
            services = serviceCatalog.findall(self._tag('service'))
            if require_service_catalog:
                self.assertTrue(len(services))
            for service in services:
                # validate service
                self.assertIsNotNone(service.get('name'))
                self.assertIsNotNone(service.get('type'))

                # services contain at least one endpoint
                endpoints = service.findall(self._tag('endpoint'))
                self.assertTrue(len(endpoints))
                for endpoint in endpoints:
                    # validate service endpoint
                    self.assertIsNotNone(endpoint.get('publicURL'))

    def assertValidTenantListResponse(self, r):
        xml = r.result
        self.assertEqual(xml.tag, self._tag('tenants'))

        self.assertTrue(len(r.result))
        for tenant in r.result.findall(self._tag('tenant')):
            self.assertValidTenant(tenant)
            self.assertIn(tenant.get('enabled'), ['true', 'false'])

    def test_authenticate_with_invalid_xml_in_password(self):
        # public_request would auto escape the ampersand
        self.public_request(
            method='POST',
            path='/v2.0/tokens',
            headers={
                'Content-Type': 'application/xml'
            },
            body="""
                <?xml version="1.0" encoding="UTF-8"?>
                <auth xmlns="http://docs.openstack.org/identity/api/v2.0"
                        tenantId="bar">
                     <passwordCredentials username="FOO" password="&"/>
                </auth>
            """,
            convert=False,
            expected_status=400)

    def test_add_tenant_xml(self):
        """
        verify create a tenant without providing description field
        """
        token = self.get_scoped_token()
        r = self.admin_request(
            method='POST',
            path='/v2.0/tenants',
            token=token,
            headers={
                'Content-Type': 'application/xml'
            },
            body="""
                <?xml version="1.0" encoding="UTF-8"?>
                <tenant xmlns="http://docs.openstack.org/identity/api/v2.0"
                enabled="true" name="ACME Corp">
                <description></description>
                </tenant>
            """,
            convert=False)
        self._from_content_type(r, 'json')
        self.assertIsNotNone(r.result.get('tenant'))
        self.assertValidTenant(r.result['tenant'])
        self.assertEqual(r.result['tenant'].get('description'), "")

    def test_add_tenant_json(self):
        """
        verify create a tenant without providing description field
        """
        token = self.get_scoped_token()
        r = self.admin_request(
            method='POST',
            path='/v2.0/tenants',
            headers={
                'Content-Type': 'application/json',
            },
            token=token,
            body="""
                {"tenant":{
                    "name":"test1",
                    "description":"",
                    "enabled":"true"}
                }
            """,
            convert=False)
        self._from_content_type(r, 'json')
        self.assertIsNotNone(r.result.get('tenant'))
        self.assertValidTenant(r.result['tenant'])
        self.assertEqual(r.result['tenant'].get('description'), "")
