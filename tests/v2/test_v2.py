
import uuid
import nose.exc

import test_content_types
import default_fixtures


class RestfulTestCase(test_content_types.RestfulTestCase):

    def setUp(self, load_sample_data=True):
        super(RestfulTestCase, self).setUp()

        self.load_backends()

        if load_sample_data:
            self.load_fixtures(default_fixtures)

            # TODO(termie): is_admin is being deprecated once the policy stuff
            #               is all working
            # TODO(termie): add an admin user to the fixtures and use that user

            # override the fixtures, for now
            self.metadata_foobar = self.identity_api.update_metadata(
                self.user_foo['id'],
                self.tenant_bar['id'],
                dict(roles=[self.role_admin['id']], is_admin='1'))

    def get_scoped_token(self):
        """Convenience method so that we can test authenticated requests."""
        r = self.public_request(
            method='POST',
            path='/v2.0/tokens',
            body={
                'auth': {
                    'passwordCredentials': {
                        'username': self.user_foo['name'],
                        'password': self.user_foo['password'],
                    },
                    'tenantId': self.tenant_bar['id'],
                },
            })
        return self._get_token_id(r)

    def _get_token_id(self, r):
        """Helper method to return a token ID from a response.

        This needs to be overridden by child classes for on their content type.

        """
        raise NotImplementedError()


class CoreApiTests(object):
    def assertValidError(self, error):
        """Applicable to XML and JSON."""
        self.assertIsNotNone(error.get('code'))
        self.assertIsNotNone(error.get('title'))
        self.assertIsNotNone(error.get('message'))

    def assertValidVersion(self, version):
        """Applicable to XML and JSON.

        However, navigating links and media-types differs between content
        types so they need to be validated separately.

        """
        self.assertIsNotNone(version)
        self.assertIsNotNone(version.get('id'))
        self.assertIsNotNone(version.get('status'))
        self.assertIsNotNone(version.get('updated'))

    def assertValidExtension(self, extension):
        """Applicable to XML and JSON.

        However, navigating extension links differs between content types.
        They need to be validated separately with assertValidExtensionLink.

        """
        self.assertIsNotNone(extension)
        self.assertIsNotNone(extension.get('name'))
        self.assertIsNotNone(extension.get('namespace'))
        self.assertIsNotNone(extension.get('alias'))
        self.assertIsNotNone(extension.get('updated'))

    def assertValidExtensionLink(self, link):
        """Applicable to XML and JSON."""
        self.assertIsNotNone(link.get('rel'))
        self.assertIsNotNone(link.get('type'))
        self.assertIsNotNone(link.get('href'))

    def assertValidTenant(self, tenant):
        """Applicable to XML and JSON."""
        self.assertIsNotNone(tenant.get('id'))
        self.assertIsNotNone(tenant.get('name'))

    def assertValidUser(self, user):
        """Applicable to XML and JSON."""
        self.assertIsNotNone(user.get('id'))
        self.assertIsNotNone(user.get('name'))

    def assertValidRole(self, tenant):
        """Applicable to XML and JSON."""
        self.assertIsNotNone(tenant.get('id'))
        self.assertIsNotNone(tenant.get('name'))

    def test_public_not_found(self):
        r = self.public_request(
            path='/%s' % uuid.uuid4().hex,
            expected_status=404)
        self.assertValidErrorResponse(r)

    def test_admin_not_found(self):
        r = self.admin_request(
            path='/%s' % uuid.uuid4().hex,
            expected_status=404)
        self.assertValidErrorResponse(r)

    def test_public_multiple_choice(self):
        r = self.public_request(path='/', expected_status=300)
        self.assertValidMultipleChoiceResponse(r)

    def test_admin_multiple_choice(self):
        r = self.admin_request(path='/', expected_status=300)
        self.assertValidMultipleChoiceResponse(r)

    def test_public_version(self):
        r = self.public_request(path='/v2.0/')
        self.assertValidVersionResponse(r)

    def test_admin_version(self):
        r = self.admin_request(path='/v2.0/')
        self.assertValidVersionResponse(r)

    def test_public_extensions(self):
        self.public_request(path='/v2.0/extensions',)

        # TODO(dolph): can't test this without any public extensions defined
        # self.assertValidExtensionListResponse(r)

    def test_admin_extensions(self):
        r = self.admin_request(path='/v2.0/extensions',)
        self.assertValidExtensionListResponse(r)

    def test_admin_extensions_404(self):
        self.admin_request(path='/v2.0/extensions/invalid-extension',
                           expected_status=404)

    def test_public_osksadm_extension_404(self):
        self.public_request(path='/v2.0/extensions/OS-KSADM',
                            expected_status=404)

    def test_admin_osksadm_extension(self):
        r = self.admin_request(path='/v2.0/extensions/OS-KSADM')
        self.assertValidExtensionResponse(r)

    def test_authenticate(self):
        r = self.public_request(
            method='POST',
            path='/v2.0/tokens',
            body={
                'auth': {
                    'passwordCredentials': {
                        'username': self.user_foo['name'],
                        'password': self.user_foo['password'],
                    },
                    'tenantId': self.tenant_bar['id'],
                },
            },
            expected_status=200)
        self.assertValidAuthenticationResponse(r, require_service_catalog=True)

    def test_authenticate_unscoped(self):
        r = self.public_request(
            method='POST',
            path='/v2.0/tokens',
            body={
                'auth': {
                    'passwordCredentials': {
                        'username': self.user_foo['name'],
                        'password': self.user_foo['password'],
                    },
                },
            },
            expected_status=200)
        self.assertValidAuthenticationResponse(r)

    def test_get_tenants_for_token(self):
        r = self.public_request(path='/v2.0/tenants',
                                token=self.get_scoped_token())
        self.assertValidTenantListResponse(r)

    def test_validate_token(self):
        token = self.get_scoped_token()
        r = self.admin_request(
            path='/v2.0/tokens/%(token_id)s' % {
                'token_id': token,
            },
            token=token)
        self.assertValidAuthenticationResponse(r)

    def test_validate_token_belongs_to(self):
        token = self.get_scoped_token()
        path = ('/v2.0/tokens/%s?belongsTo=%s' % (token,
                                                  self.tenant_bar['id']))
        r = self.admin_request(path=path, token=token)
        self.assertValidAuthenticationResponse(r, require_service_catalog=True)

    def test_validate_token_no_belongs_to_still_returns_catalog(self):
        token = self.get_scoped_token()
        path = ('/v2.0/tokens/%s' % token)
        r = self.admin_request(path=path, token=token)
        self.assertValidAuthenticationResponse(r, require_service_catalog=True)

    def test_validate_token_head(self):
        """The same call as above, except using HEAD.

        There's no response to validate here, but this is included for the
        sake of completely covering the core API.

        """
        token = self.get_scoped_token()
        self.admin_request(
            method='HEAD',
            path='/v2.0/tokens/%(token_id)s' % {
                'token_id': token,
            },
            token=token,
            expected_status=204)

    def test_endpoints(self):
        token = self.get_scoped_token()
        r = self.admin_request(
            path='/v2.0/tokens/%(token_id)s/endpoints' % {
                'token_id': token,
            },
            token=token)
        self.assertValidEndpointListResponse(r)

    def test_get_tenant(self):
        token = self.get_scoped_token()
        r = self.admin_request(
            path='/v2.0/tenants/%(tenant_id)s' % {
                'tenant_id': self.tenant_bar['id'],
            },
            token=token)
        self.assertValidTenantResponse(r)

    def test_get_tenant_by_name(self):
        token = self.get_scoped_token()
        r = self.admin_request(
            path='/v2.0/tenants?name=%(tenant_name)s' % {
                'tenant_name': self.tenant_bar['name'],
            },
            token=token)
        self.assertValidTenantResponse(r)

    def test_get_user_roles(self):
        raise nose.exc.SkipTest('Blocked by bug 933565')

        token = self.get_scoped_token()
        r = self.admin_request(
            path='/v2.0/users/%(user_id)s/roles' % {
                'user_id': self.user_foo['id'],
            },
            token=token)
        self.assertValidRoleListResponse(r)

    def test_get_user_roles_with_tenant(self):
        token = self.get_scoped_token()
        r = self.admin_request(
            path='/v2.0/tenants/%(tenant_id)s/users/%(user_id)s/roles' % {
                'tenant_id': self.tenant_bar['id'],
                'user_id': self.user_foo['id'],
            },
            token=token)
        self.assertValidRoleListResponse(r)

    def test_get_user(self):
        token = self.get_scoped_token()
        r = self.admin_request(
            path='/v2.0/users/%(user_id)s' % {
                'user_id': self.user_foo['id'],
            },
            token=token)
        self.assertValidUserResponse(r)

    def test_get_user_by_name(self):
        token = self.get_scoped_token()
        r = self.admin_request(
            path='/v2.0/users?name=%(user_name)s' % {
                'user_name': self.user_foo['name'],
            },
            token=token)
        self.assertValidUserResponse(r)

    def test_error_response(self):
        """This triggers assertValidErrorResponse by convention."""
        self.public_request(path='/v2.0/tenants', expected_status=401)

    def test_invalid_parameter_error_response(self):
        token = self.get_scoped_token()
        bad_body = {
            'OS-KSADM:service%s' % uuid.uuid4().hex: {
                'name': uuid.uuid4().hex,
                'type': uuid.uuid4().hex,
            },
        }
        res = self.admin_request(method='POST',
                                 path='/v2.0/OS-KSADM/services',
                                 body=bad_body,
                                 token=token,
                                 expected_status=400)
        self.assertValidErrorResponse(res)
        res = self.admin_request(method='POST',
                                 path='/v2.0/users',
                                 body=bad_body,
                                 token=token,
                                 expected_status=400)
        self.assertValidErrorResponse(res)


class JsonTestCase(RestfulTestCase, CoreApiTests):
    content_type = 'json'

    def _get_token_id(self, r):
        """Applicable only to JSON."""
        return r.result['access']['token']['id']

    def assertValidErrorResponse(self, r):
        self.assertIsNotNone(r.result.get('error'))
        self.assertValidError(r.result['error'])
        self.assertEqual(r.result['error']['code'], r.status_code)

    def assertValidExtension(self, extension):
        super(JsonTestCase, self).assertValidExtension(extension)

        self.assertIsNotNone(extension.get('description'))
        self.assertIsNotNone(extension.get('links'))
        self.assertTrue(len(extension.get('links')))
        for link in extension.get('links'):
            self.assertValidExtensionLink(link)

    def assertValidExtensionListResponse(self, r):
        self.assertIsNotNone(r.result.get('extensions'))
        self.assertIsNotNone(r.result['extensions'].get('values'))
        self.assertTrue(len(r.result['extensions'].get('values')))
        for extension in r.result['extensions']['values']:
            self.assertValidExtension(extension)

    def assertValidExtensionResponse(self, r):
        self.assertValidExtension(r.result.get('extension'))

    def assertValidAuthenticationResponse(self, r,
                                          require_service_catalog=False):
        self.assertIsNotNone(r.result.get('access'))
        self.assertIsNotNone(r.result['access'].get('token'))
        self.assertIsNotNone(r.result['access'].get('user'))

        # validate token
        self.assertIsNotNone(r.result['access']['token'].get('id'))
        self.assertIsNotNone(r.result['access']['token'].get('expires'))
        tenant = r.result['access']['token'].get('tenant')
        if tenant is not None:
            # validate tenant
            self.assertIsNotNone(tenant.get('id'))
            self.assertIsNotNone(tenant.get('name'))

        # validate user
        self.assertIsNotNone(r.result['access']['user'].get('id'))
        self.assertIsNotNone(r.result['access']['user'].get('name'))

        if require_service_catalog:
            # roles are only provided with a service catalog
            roles = r.result['access']['user'].get('roles')
            self.assertTrue(len(roles))
            for role in roles:
                self.assertIsNotNone(role.get('name'))

        serviceCatalog = r.result['access'].get('serviceCatalog')
        # validate service catalog
        if require_service_catalog:
            self.assertIsNotNone(serviceCatalog)
        if serviceCatalog is not None:
            self.assertTrue(isinstance(serviceCatalog, list))
            if require_service_catalog:
                self.assertTrue(len(serviceCatalog))
            for service in r.result['access']['serviceCatalog']:
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
        self.assertIsNotNone(r.result.get('tenants'))
        self.assertTrue(len(r.result['tenants']))
        for tenant in r.result['tenants']:
            self.assertValidTenant(tenant)
            self.assertIsNotNone(tenant.get('enabled'))
            self.assertIn(tenant.get('enabled'), [True, False])

    def assertValidUserResponse(self, r):
        self.assertIsNotNone(r.result.get('user'))
        self.assertValidUser(r.result['user'])

    def assertValidTenantResponse(self, r):
        self.assertIsNotNone(r.result.get('tenant'))
        self.assertValidTenant(r.result['tenant'])

    def assertValidRoleListResponse(self, r):
        self.assertIsNotNone(r.result.get('roles'))
        self.assertTrue(len(r.result['roles']))
        for role in r.result['roles']:
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
        self.assertIsNotNone(r.result.get('versions'))
        self.assertIsNotNone(r.result['versions'].get('values'))
        self.assertTrue(len(r.result['versions']['values']))
        for version in r.result['versions']['values']:
            self.assertValidVersion(version)

    def assertValidVersionResponse(self, r):
        self.assertValidVersion(r.result.get('version'))

    def assertValidEndpointListResponse(self, r):
        self.assertIsNotNone(r.result.get('endpoints'))
        self.assertTrue(len(r.result['endpoints']))
        for endpoint in r.result['endpoints']:
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
        r = self.admin_request(
            method='GET',
            path='/v2.0/tokens/revoked',
            token=token,
            expected_status=200)
        self.assertValidRevocationListResponse(r)

    def assertValidRevocationListResponse(self, response):
        self.assertIsNotNone(response.result['signed'])


class XmlTestCase(RestfulTestCase, CoreApiTests):
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
