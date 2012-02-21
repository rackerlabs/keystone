# vim: tabstop=4 shiftwidth=4 softtabstop=4

import httplib
import json
from lxml import etree
import nose.exc

from keystone import test
from keystone.common import serializer

import default_fixtures


class ContentTestCase(test.TestCase):
    """Performs tests against the WSGI app over HTTP.

    Defines a ``request`` method for use in test cases that makes
    HTTP requests, and two new asserts:

    * assertResponseSuccessful
    * assertResponseStatus

    """

    def setUp(self):
        super(ContentTestCase, self).setUp()

        self.load_backends()
        self.load_fixtures(default_fixtures)

        self.public_server = self.serveapp('keystone', name='main')
        self.admin_server = self.serveapp('keystone', name='admin')

        # TODO(termie): is_admin is being deprecated once the policy stuff
        #               is all working
        # TODO(termie): add an admin user to the fixtures and use that user
        # override the fixtures, for now
        self.metadata_foobar = self.identity_api.update_metadata(
            self.user_foo['id'], self.tenant_bar['id'],
            dict(roles=['keystone_admin'], is_admin='1'))

    def tearDown(self):
        self.public_server.kill()
        self.admin_server.kill()
        self.public_server = None
        self.admin_server = None
        super(ContentTestCase, self).tearDown()

    def request(self, host='0.0.0.0', port=80, method='GET', path='/',
            headers=None, body=None, expected_status=None):
        """Perform request and fetch httplib.HTTPResponse from the server."""

        # Initialize headers dictionary
        headers = {} if not headers else headers

        connection = httplib.HTTPConnection(host, port, timeout=10)

        # Perform the request
        connection.request(method, path, body, headers)

        # Retrieve the response so we can close the connection
        response = connection.getresponse()

        response.body = response.read()

        # Close the connection
        connection.close()

        # Automatically assert HTTP status code
        if expected_status:
            self.assertResponseStatus(response, expected_status)
        else:
            self.assertResponseSuccessful(response)

        # Contains the response headers, body, etc
        return response

    def assertResponseSuccessful(self, response):
        """Asserts that a status code lies inside the 2xx range

        :param response: :py:class:`httplib.HTTPResponse` to be
          verified to have a status code between 200 and 299.

        example::

            >>> self.assertResponseSuccessful(response, 203)
        """
        self.assertTrue(response.status >= 200 and response.status <= 299,
            'Status code %d is outside of the expected range (2xx)\n\n%s' %
            (response.status, response.body))

    def assertResponseStatus(self, response, expected_status):
        """Asserts a specific status code on the response

        :param response: :py:class:`httplib.HTTPResponse`
        :param assert_status: The specific ``status`` result expected

        example::

            >>> self.assertResponseStatus(response, 203)
        """
        self.assertEqual(response.status, expected_status,
            'Status code %s is not %s, as expected)\n\n%s' %
            (response.status, expected_status, response.body))

    def assertValidErrorResponse(self, r):
        """Applicable only to JSON."""
        self.assertIsNotNone(r.body.get('error'))
        self.assertValidError(r.body['error'])
        self.assertEqual(r.body['error']['code'], r.status)

    def assertValidError(self, error):
        """For JSON & XML."""
        self.assertIsNotNone(error.get('code'))
        self.assertIsNotNone(error.get('title'))
        self.assertIsNotNone(error.get('message'))

    # default content type to test
    content_type = 'json'

    def restful_request(self, headers=None, body=None, token=None, **kwargs):
        """Serializes/deserializes json/xml as request/response body.

        .. WARNING::

            * Existing Accept header will be overwritten.
            * Existing Content-Type header will be overwritten.

        """
        # Initialize headers dictionary
        headers = {} if not headers else headers

        if token is not None:
            headers['X-Auth-Token'] = token

        # Attempt to encode JSON and XML automatically
        if self.content_type == 'json':
            headers['Accept'] = 'application/json'
            if body:
                headers['Content-Type'] = 'application/json'
                body = json.dumps(body)
        elif self.content_type == 'xml':
            headers['Accept'] = 'application/xml'
            if body:
                headers['Content-Type'] = 'application/xml'
                body = serializer.to_xml(body)

        # Perform the HTTP request/response
        response = self.request(headers=headers, body=body, **kwargs)

        # Attempt to parse JSON and XML automatically, if detected
        if response.body is not None and response.body.strip():
            response.raw = response.body
            print response.raw

            # if a body is provided, a Content-Type is also expected
            header = response.getheader('Content-Type', None)
            self.assertIn(self.content_type, header)

            if self.content_type == 'json':
                response.body = json.loads(response.body)
            elif self.content_type == 'xml':
                response.body = etree.fromstring(response.body)

        # we can save some code & improve coverage by always doing this
        if response.status >= 400:
            self.assertValidErrorResponse(response)

        # Contains the decoded response.body
        return response

    def public_request(self, port=None, **kwargs):
        kwargs['port'] = port or self.public_server.socket_info['socket'][1]
        return self.restful_request(**kwargs)

    def admin_request(self, port=None, **kwargs):
        kwargs['port'] = port or self.admin_server.socket_info['socket'][1]
        return self.restful_request(**kwargs)

    def get_scoped_token(self):
        r = self.public_request(method='POST', path='/v2.0/tokens', body={
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


class JsonTestCase(ContentTestCase):
    content_type = 'json'

    def _get_token_id(self, r):
        """Applicable only to JSON."""
        return r.body['access']['token']['id']

    def assertValidAuthenticationResponse(self, r):
        """Applicable only to JSON."""
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

        # validate service catalog
        if r.body['access'].get('serviceCatalog') is not None:
            self.assertTrue(len(r.body['access']['serviceCatalog']))
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

    def assertValidTenantListResponse(self, r):
        """Applicable only to JSON."""
        self.assertIsNotNone(r.body.get('tenants'))
        self.assertTrue(len(r.body['tenants']))
        for tenant in r.body['tenants']:
            self.assertValidTenant(tenant)
            self.assertIsNotNone(tenant.get('enabled'))
            self.assertIn(tenant.get('enabled'), [True, False])

    def assertValidUserResponse(self, r):
        """Applicable only to JSON."""
        self.assertIsNotNone(r.body.get('user'))
        self.assertValidUser(r.body['user'])

    def assertValidTenantResponse(self, r):
        """Applicable only to JSON."""
        self.assertIsNotNone(r.body.get('tenant'))
        self.assertValidTenant(r.body['tenant'])

    def assertValidRoleListResponse(self, r):
        """Applicable only to JSON."""
        self.assertIsNotNone(r.body.get('roles'))
        self.assertTrue(len(r.body['roles']))
        for role in r.body['roles']:
            self.assertValidRole(role)

    def assertValidMultipleChoiceResponse(self, r):
        """Applicable only to JSON."""
        self.assertIsNotNone(r.body.get('versions'))
        self.assertIsNotNone(r.body['versions'].get('values'))
        self.assertTrue(len(r.body['versions']['values']))
        for version in r.body['versions']['values']:
            self.assertIsNotNone(version.get('id'))
            self.assertIsNotNone(version.get('status'))
            self.assertIsNotNone(version.get('updated'))
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

    def assertValidVersionResponse(self, r):
        """Applicable only to JSON."""
        raise NotImplementedError()

    def test_public_multiple_choice_response(self):
        r = self.public_request(path='/', expected_status=300)
        self.assertValidMultipleChoiceResponse(r)

    def test_admin_multiple_choice_response(self):
        r = self.admin_request(path='/', expected_status=300)
        self.assertValidMultipleChoiceResponse(r)

    def test_public_version_response(self):
        raise nose.exc.SkipTest('Blocked by bug 925548')

        r = self.public_request(path='/v2.0/')
        self.assertValidVersionResponse(r)

    def test_admin_version_response(self):
        raise nose.exc.SkipTest('Blocked by bug 925548')

        r = self.admin_request(path='/v2.0/')
        self.assertValidVersionResponse(r)

    def test_public_extensions_response(self):
        raise nose.exc.SkipTest('Blocked by bug 928054')

        self.public_request(path='/v2.0/extensions',)

    def test_admin_extensions_response(self):
        raise nose.exc.SkipTest('Blocked by bug 928054')

        self.admin_request(path='/v2.0/extensions',)

    def test_authentication(self):
        # authenticate: POST /v2.0/tokens
        r = self.public_request(method='POST', path='/v2.0/tokens', body={
                'auth': {
                    'passwordCredentials': {
                        'username': self.user_foo['name'],
                        'password': self.user_foo['password'],
                    },
                    'tenantId': self.tenant_bar['id'],
                },
            },
            # TODO(dolph): creating a token should result in a 201 Created
            expected_status=200)
        self.assertValidAuthenticationResponse(r)

    def test_tenant_list(self):
        r = self.public_request(path='/v2.0/tenants',
            token=self.get_scoped_token())
        self.assertValidTenantListResponse(r)

    def test_token_validation(self):
        token = self.get_scoped_token()
        r = self.admin_request(path='/v2.0/tokens/%(token_id)s' % {
                'token_id': token,
            },
            token=token)
        self.assertValidAuthenticationResponse(r)

    def test_token_validation_head(self):
        """The same call as above, except using HEAD.

        There's no response to validate here, but this is included for the
        sake of completely covering core.

        """
        token = self.get_scoped_token()
        self.admin_request(method='HEAD', path='/v2.0/tokens/%(token_id)s' % {
                'token_id': token,
            },
            token=token,
            expected_status=204)

    def test_token_endpoints(self):
        raise nose.exc.SkipTest('Blocked by bug 933555')

        token = self.get_scoped_token()
        r = self.admin_request(path='/v2.0/tokens/%(token_id)s/endpoints' % {
                'token_id': token,
            },
            token=token)
        self.assertValidTokenCatalogResponse(r)

    def test_tenant_details(self):
        token = self.get_scoped_token()
        r = self.admin_request(path='/v2.0/tenants/%(tenant_id)s' % {
                'tenant_id': self.tenant_bar['id'],
            },
            token=token)
        self.assertValidTenantResponse(r)

    def test_granted_roles(self):
        raise nose.exc.SkipTest('Blocked by bug 933565')

        token = self.get_scoped_token()
        r = self.admin_request(path='/v2.0/users/%(user_id)s/roles' % {
                'user_id': self.user_foo['id'],
            },
            token=token)
        self.assertValidRoleListResponse(r)

    def test_granted_roles_on_a_tenant(self):
        token = self.get_scoped_token()
        r = self.admin_request(path='/v2.0/tenants/%(tenant_id)s/users/%(user_id)s/roles' % {
                'tenant_id': self.tenant_bar['id'],
                'user_id': self.user_foo['id'],
            },
            token=token)
        self.assertValidRoleListResponse(r)

    def test_user_details(self):
        token = self.get_scoped_token()
        r = self.admin_request(path='/v2.0/users/%(user_id)s' % {
                'user_id': self.user_foo['id'],
            },
            token=token)
        self.assertValidUserResponse(r)

    def test_error_response(self):
        self.public_request(path='/v2.0/tenants', expected_status=401)


class XmlTestCase(JsonTestCase):
    """This XML test case extends the JSON tests to make assertions about XML.

    """
    xmlns = 'http://docs.openstack.org/identity/api/v2.0'
    content_type = 'xml'

    def _get_token_id(self, r):
        return r.body.find(self._tag('token')).get('id')

    def _tag(self, tag_name, xmlns=None):
        """Helper method to build an namespaced element name"""
        return '{%(ns)s}%(tag)s' % {'ns': xmlns or self.xmlns, 'tag': tag_name}

    def assertValidErrorResponse(self, r):
        """Applicable only to XML."""
        xml = r.body
        self.assertEqual(xml.tag, self._tag('error'))

        self.assertValidError(xml)
        self.assertEqual(xml.get('code'), str(r.status))

    def assertValidMultipleChoiceResponse(self, r):
        """Applicable only to XML."""
        xml = r.body
        self.assertEqual(xml.tag, self._tag('versions'))

        self.assertTrue(len(xml.findall(self._tag('version'))))
        for version in xml.findall(self._tag('version')):
            # validate service endpoint
            self.assertIsNotNone(version.get('id'))
            self.assertIsNotNone(version.get('status'))
            self.assertIsNotNone(version.get('updated'))

            self.assertTrue(len(version.findall(self._tag('link'))))
            for link in version.findall(self._tag('link')):
                self.assertIsNotNone(link.get('rel'))
                self.assertIsNotNone(link.get('href'))

            media_types = version.find(self._tag('media-types'))
            self.assertIsNotNone(media_types)
            self.assertTrue(len(media_types.findall(self._tag('media-type'))))
            for media in media_types.findall(self._tag('media-type')):
                self.assertIsNotNone(media.get('base'))
                self.assertIsNotNone(media.get('type'))

    def assertValidVersionResponse(self, r):
        """Applicable only to XML."""
        raise NotImplementedError()

    def assertValidTokenCatalogResponse(self, r):
        """Applicable only to XML."""
        xml = r.body
        self.assertEqual(xml.tag, self._tag('endpoints'))

        self.assertTrue(len(xml.findall(self._tag('endpoint'))))
        for endpoint in xml.findall(self._tag('endpoint')):
            self.assertIsNotNone(endpoint.get('publicUrl'))

    def assertValidTenantResponse(self, r):
        """Applicable only to XML."""
        xml = r.body
        self.assertEqual(xml.tag, self._tag('tenant'))

        self.assertValidTenant(xml)

    def assertValidUserResponse(self, r):
        """Applicable only to XML."""
        xml = r.body
        self.assertEqual(xml.tag, self._tag('user'))

        self.assertValidUser(xml)

    def assertValidRoleListResponse(self, r):
        """Applicable only to XML."""
        xml = r.body
        self.assertEqual(xml.tag, self._tag('roles'))

        self.assertTrue(len(r.body.findall(self._tag('role'))))
        for role in r.body.findall(self._tag('role')):
            self.assertValidRole(role)

    def assertValidAuthenticationResponse(self, r):
        """Applicable only to XML."""
        xml = r.body
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

        serviceCatalog = xml.find(self._tag('serviceCatalog'))
        if serviceCatalog is not None:
            self.assertTrue(len(serviceCatalog.findall(self._tag('service'))))
            for service in serviceCatalog.findall(self._tag('service')):
                # validate service
                self.assertIsNotNone(service.get('name'))
                self.assertIsNotNone(service.get('type'))

                # services contain at least one endpoint
                self.assertTrue(len(service))
                for endpoint in service.findall(self._tag('endpoint')):
                    # validate service endpoint
                    self.assertIsNotNone(endpoint.get('publicURL'))

    def assertValidTenantListResponse(self, r):
        """Applicable only to XML."""
        xml = r.body
        self.assertEqual(xml.tag, self._tag('tenants'))

        self.assertTrue(len(r.body))
        for tenant in r.body.findall(self._tag('tenant')):
            self.assertValidTenant(tenant)
            self.assertIn(tenant.get('enabled'), ['true', 'false'])
