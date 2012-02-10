# vim: tabstop=4 shiftwidth=4 softtabstop=4

import httplib
import json

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
        """Perform request and fetch httplib.HTTPResponse from the server"""

        # Initialize headers dictionary
        headers = {} if not headers else headers

        connection = httplib.HTTPConnection(host, port, timeout=10)

        # Perform the request
        # print headers # TODO(dolph): remove before merging
        connection.request(method, path, body, headers)

        # Retrieve the response so we can close the connection
        response = connection.getresponse()

        response.body = response.read()
        # print response.getheaders() # TODO(dolph): remove before merging
        # print response.body # TODO(dolph): remove before merging

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

    # default content type to test
    content_type = 'json'

    def restful_request(self, headers=None, body=None, **kwargs):
        """Serializes/deserializes json/xml as request/response body.

        .. WARNING::

            * Existing Accept header will be overwritten.
            * Existing Content-Type header will be overwritten.

        """
        # Initialize headers dictionary
        headers = {} if not headers else headers

        # Attempt to encode JSON and XML automatically
        if self.content_type == 'json':
            headers['Accept'] = 'application/json'
            headers['Content-Type'] = 'application/json'
            body = json.dumps(body)
        elif self.content_type == 'xml':
            headers['Accept'] = 'application/xml'
            headers['Content-Type'] = 'application/xml'
            body = serializer.to_xml(body)

        # Perform the HTTP request/response
        response = self.request(headers=headers, body=body, **kwargs)

        # Attempt to parse JSON and XML automatically, if detected
        if response.body is not None and response.body.strip():
            # if a body is provided, a Content-Type is also expected
            header = response.getheader('Content-Type', None)
            self.assertIn(self.content_type, header)

            if self.content_type == 'json':
                response.body = json.loads(response.body)
            elif self.content_type == 'xml':
                response.body = serializer.from_xml(response.body)

        # Contains the decoded response.body
        return response

    def public_request(self, port=None, **kwargs):
        kwargs['port'] = port or self.public_server.socket_info['socket'][1]
        return self.restful_request(**kwargs)

    def admin_request(self, port=None, **kwargs):
        kwargs['port'] = port or self.admin_server.socket_info['socket'][1]
        return self.restful_request(**kwargs)


class JsonTestCase(ContentTestCase):
    content_type = 'json'

    def assertValidErrorResponse(self, r):
        self.assertIsNotNone(r.body.get('error'))
        self.assertIsNotNone(r.body['error'].get('code'))
        self.assertIsNotNone(r.body['error'].get('title'))
        self.assertIsNotNone(r.body['error'].get('message'))
        self.assertEqual(str(r.body['error']['code']), str(r.status))

    def test_public_request(self):
        r = self.public_request(path='/v2.0/tenants', expected_status=401)
        self.assertValidErrorResponse(r)

    def test_admin_request(self):
        r = self.admin_request(path='/v2.0/tenants', expected_status=401)
        self.assertValidErrorResponse(r)


class XmlTestCase(JsonTestCase):
    content_type = 'xml'
