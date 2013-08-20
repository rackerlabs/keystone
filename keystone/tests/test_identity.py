# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack Foundation
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

import io
import uuid

from lxml import etree
import webtest

from keystone import tests

from keystone.common import extension
from keystone.common import serializer
from keystone.openstack.common import jsonutils

import default_fixtures


class RestfulTestCase(tests.TestCase):
    """Performs restful tests against the WSGI app over HTTP.

    This class launches public & admin WSGI servers for every test, which can
    be accessed by calling ``public_request()`` or ``admin_request()``,
    respectfully.

    ``restful_request()`` and ``request()`` methods are also exposed if you
    need to bypass restful conventions or access HTTP details in your test
    implementation.

    Three new asserts are provided:

    * ``assertResponseSuccessful``: called automatically for every request
        unless an ``expected_status`` is provided
    * ``assertResponseStatus``: called instead of ``assertResponseSuccessful``,
        if an ``expected_status`` is provided
    * ``assertValidResponseHeaders``: validates that the response headers
        appear as expected

    Requests are automatically serialized according to the defined
    ``content_type``. Responses are automatically deserialized as well, and
    available in the ``response.body`` attribute. The original body content is
    available in the ``response.raw`` attribute.

    """

    # default content type to test
    content_type = 'json'

    def setUp(self):
        super(RestfulTestCase, self).setUp()

        self.load_backends()
        self.load_fixtures(default_fixtures)

        self.public_app = webtest.TestApp(
            self.loadapp('keystone', name='main'))
        self.admin_app = webtest.TestApp(
            self.loadapp('keystone', name='admin'))

        # TODO(termie): add an admin user to the fixtures and use that user
        # override the fixtures, for now
        self.metadata_foobar = self.identity_api.add_role_to_user_and_project(
            self.user_foo['id'],
            self.tenant_bar['id'],
            self.role_admin['id'])

    def tearDown(self):
        """Kill running servers and release references to avoid leaks."""
        self.public_app = None
        self.admin_app = None
        super(RestfulTestCase, self).tearDown()

    def request(self, app, path, body=None, headers=None, token=None,
                expected_status=None, **kwargs):
        if headers:
            headers = dict([(str(k), str(v)) for k, v in headers.iteritems()])
        else:
            headers = {}

        if token:
            headers['X-Auth-Token'] = str(token)

        # setting body this way because of:
        # https://github.com/Pylons/webtest/issues/71
        if body:
            kwargs['body_file'] = io.BytesIO(body)

        # sets environ['REMOTE_ADDR']
        kwargs.setdefault('remote_addr', 'localhost')

        response = app.request(path, headers=headers,
                               status=expected_status, **kwargs)

        return response

    def assertResponseSuccessful(self, response):
        """Asserts that a status code lies inside the 2xx range.

        :param response: :py:class:`httplib.HTTPResponse` to be
          verified to have a status code between 200 and 299.

        example::

             self.assertResponseSuccessful(response, 203)
        """
        self.assertTrue(
            response.status_code >= 200 and response.status_code <= 299,
            'Status code %d is outside of the expected range (2xx)\n\n%s' %
            (response.status, response.body))

    def assertResponseStatus(self, response, expected_status):
        """Asserts a specific status code on the response.

        :param response: :py:class:`httplib.HTTPResponse`
        :param assert_status: The specific ``status`` result expected

        example::

            self.assertResponseStatus(response, 203)
        """
        self.assertEqual(
            response.status_code,
            expected_status,
            'Status code %s is not %s, as expected)\n\n%s' %
            (response.status_code, expected_status, response.body))

    def assertValidResponseHeaders(self, response):
        """Ensures that response headers appear as expected."""
        self.assertIn('X-Auth-Token', response.headers.get('Vary'))

    def _to_content_type(self, body, headers, content_type=None):
        """Attempt to encode JSON and XML automatically."""
        content_type = content_type or self.content_type

        if content_type == 'json':
            headers['Accept'] = 'application/json'
            if body:
                headers['Content-Type'] = 'application/json'
                return jsonutils.dumps(body)
        elif content_type == 'xml':
            headers['Accept'] = 'application/xml'
            if body:
                headers['Content-Type'] = 'application/xml'
                return serializer.to_xml(body)

    def _from_content_type(self, response, content_type=None):
        """Attempt to decode JSON and XML automatically, if detected."""
        content_type = content_type or self.content_type

        if response.body is not None and response.body.strip():
            # if a body is provided, a Content-Type is also expected
            header = response.headers.get('Content-Type', None)
            self.assertIn(content_type, header)

            if content_type == 'json':
                response.result = jsonutils.loads(response.body)
            elif content_type == 'xml':
                response.result = etree.fromstring(response.body)

    def restful_request(self, method='GET', headers=None, body=None,
                        content_type=None, **kwargs):
        """Serializes/deserializes json/xml as request/response body.

        .. WARNING::

            * Existing Accept header will be overwritten.
            * Existing Content-Type header will be overwritten.

        """
        # Initialize headers dictionary
        headers = {} if not headers else headers

        body = self._to_content_type(body, headers, content_type)

        # Perform the HTTP request/response
        response = self.request(method=method, headers=headers, body=body,
                                **kwargs)

        self._from_content_type(response, content_type)

        # we can save some code & improve coverage by always doing this
        if method != 'HEAD' and response.status_code >= 400:
            self.assertValidErrorResponse(response)

        # Contains the decoded response.body
        return response

    def _request(self, convert=True, **kwargs):
        if convert:
            response = self.restful_request(**kwargs)
        else:
            response = self.request(**kwargs)

        self.assertValidResponseHeaders(response)
        return response

    def public_request(self, **kwargs):
        return self._request(app=self.public_app, **kwargs)

    def admin_request(self, **kwargs):
        return self._request(app=self.admin_app, **kwargs)

    def _get_token(self, body):
        """Convenience method so that we can test authenticated requests."""
        r = self.public_request(method='POST', path='/v2.0/tokens', body=body)
        return self._get_token_id(r)

    def get_unscoped_token(self):
        """Convenience method so that we can test authenticated requests."""
        return self._get_token({
            'auth': {
                'passwordCredentials': {
                    'username': self.user_foo['name'],
                    'password': self.user_foo['password'],
                },
            },
        })

    def get_scoped_token(self, tenant_id=None):
        """Convenience method so that we can test authenticated requests."""
        if not tenant_id:
            tenant_id = self.tenant_bar['id']
        return self._get_token({
            'auth': {
                'passwordCredentials': {
                    'username': self.user_foo['name'],
                    'password': self.user_foo['password'],
                },
                'tenantId': tenant_id,
            },
        })

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

class JsonTestCase(RestfulTestCase, CoreApiTests):
    content_type = 'json'

    def _get_token_id(self, r):
        """Applicable only to JSON."""
        return r.result['access']['token']['id']

    def assertValidErrorResponse(self, r):
        self.assertIsNotNone(r.result.get('error'))
        self.assertValidError(r.result['error'])
        self.assertEqual(r.result['error']['code'], r.status_code)

    def assertValidExtension(self, extension, expected):
        super(JsonTestCase, self).assertValidExtension(extension)
        descriptions = [ext['description'] for ext in expected.itervalues()]
        description = extension.get('description')
        self.assertIsNotNone(description)
        self.assertIn(description, descriptions)
        self.assertIsNotNone(extension.get('links'))
        self.assertNotEmpty(extension.get('links'))
        for link in extension.get('links'):
            self.assertValidExtensionLink(link)

    def assertValidExtensionListResponse(self, r, expected):
        self.assertIsNotNone(r.result.get('extensions'))
        self.assertIsNotNone(r.result['extensions'].get('values'))
        self.assertNotEmpty(r.result['extensions'].get('values'))
        for extension in r.result['extensions']['values']:
            self.assertValidExtension(extension, expected)

    def assertValidExtensionResponse(self, r, expected):
        self.assertValidExtension(r.result.get('extension'), expected)

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
            self.assertNotEmpty(roles)
            for role in roles:
                self.assertIsNotNone(role.get('name'))

        serviceCatalog = r.result['access'].get('serviceCatalog')
        # validate service catalog
        if require_service_catalog:
            self.assertIsNotNone(serviceCatalog)
        if serviceCatalog is not None:
            self.assertTrue(isinstance(serviceCatalog, list))
            if require_service_catalog:
                self.assertNotEmpty(serviceCatalog)
            for service in r.result['access']['serviceCatalog']:
                # validate service
                self.assertIsNotNone(service.get('name'))
                self.assertIsNotNone(service.get('type'))

                # services contain at least one endpoint
                self.assertIsNotNone(service.get('endpoints'))
                self.assertNotEmpty(service['endpoints'])
                for endpoint in service['endpoints']:
                    # validate service endpoint
                    self.assertIsNotNone(endpoint.get('publicURL'))

    def assertValidTenantListResponse(self, r):
        self.assertIsNotNone(r.result.get('tenants'))
        self.assertNotEmpty(r.result['tenants'])
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
        self.assertNotEmpty(r.result['roles'])
        for role in r.result['roles']:
            self.assertValidRole(role)

    def assertValidVersion(self, version):
        super(JsonTestCase, self).assertValidVersion(version)

        self.assertIsNotNone(version.get('links'))
        self.assertNotEmpty(version.get('links'))
        for link in version.get('links'):
            self.assertIsNotNone(link.get('rel'))
            self.assertIsNotNone(link.get('href'))

        self.assertIsNotNone(version.get('media-types'))
        self.assertNotEmpty(version.get('media-types'))
        for media in version.get('media-types'):
            self.assertIsNotNone(media.get('base'))
            self.assertIsNotNone(media.get('type'))

    def assertValidMultipleChoiceResponse(self, r):
        self.assertIsNotNone(r.result.get('versions'))
        self.assertIsNotNone(r.result['versions'].get('values'))
        self.assertNotEmpty(r.result['versions']['values'])
        for version in r.result['versions']['values']:
            self.assertValidVersion(version)

    def assertValidVersionResponse(self, r):
        self.assertValidVersion(r.result.get('version'))

    def assertValidEndpointListResponse(self, r):
        self.assertIsNotNone(r.result.get('endpoints'))
        self.assertNotEmpty(r.result['endpoints'])
        for endpoint in r.result['endpoints']:
            self.assertIsNotNone(endpoint.get('id'))
            self.assertIsNotNone(endpoint.get('name'))
            self.assertIsNotNone(endpoint.get('type'))
            self.assertIsNotNone(endpoint.get('publicURL'))
            self.assertIsNotNone(endpoint.get('internalURL'))
            self.assertIsNotNone(endpoint.get('adminURL'))

    def test_update_user(self):
        token = self.get_scoped_token()

        # Create a new user
        r = self.admin_request(
            method='POST',
            path='/v2.0/users',
            body={
                'user': {
                    'name': uuid.uuid4().hex,
                    'password': uuid.uuid4().hex,
                    'tenantId': self.tenant_bar['id'],
                    'enabled': True,
                },
            },
            token=token,
            expected_status=200)

        user_id = r.result['user']['id']

        # Check if member_role is in tenant_bar
        r = self.admin_request(
            method='GET',
            path='/v2.0/tenants/' + self.tenant_bar['id']
                + '/users/' + user_id + '/roles',
            body={},
            token=token,
            expected_status=200)
        self.assertEqual(r.result['roles'][0]['name'], '_member_')
        member_role_id = r.result['roles'][0]['id']

        # Create a new tenant
        r = self.admin_request(
            method='POST',
            path='/v2.0/tenants',
            body={
                'tenant': {
                    'name': 'test_update_user',
                    'description': 'A description ...',
                    'enabled': True,
                 },
            },
            token=token,
            expected_status=200)

        project_id = r.result['tenant']['id']

        # Update user's tenant
        r = self.admin_request(
            method='PUT',
            path='/v2.0/users/%(user_id)s' % {
                 'user_id': user_id,
            },
            body={
                'user': {
                    'tenantId': project_id,
                },
            },
            token=token,
            expected_status=200)

        # 'member_role' should be in new_tenant
        r = self.admin_request(
            method='GET',
            path='/v2.0/tenants/' + project_id
                + '/users/' + user_id + '/roles',
            body={},
            token=token,
            expected_status=200)
        self.assertEqual(r.result['roles'][0]['name'], '_member_')

        # 'member_role' should not be in tenant_bar any more
        r = self.admin_request(
            method='GET',
            path='/v2.0/tenants/' + self.tenant_bar['id']
                + '/users/' + user_id + '/roles',
            body={},
            token=token,
            expected_status=200)
        self.assertEqual(r.result['roles'], [])
