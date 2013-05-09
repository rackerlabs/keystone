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

import httplib
from lxml import etree

from keystone.common import serializer
from keystone.openstack.common import jsonutils
from keystone import test


class RestfulTestCase(test.TestCase):
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

        self.public_server = self.serveapp('keystone', name='main')
        self.admin_server = self.serveapp('keystone', name='admin')

    def tearDown(self):
        """Kill running servers and release references to avoid leaks."""
        self.public_server.kill()
        self.admin_server.kill()
        self.public_server = None
        self.admin_server = None
        super(RestfulTestCase, self).tearDown()

    def request(self, host='0.0.0.0', port=80, method='GET', path='/',
                headers=None, body=None, expected_status=None):
        """Perform request and fetch httplib.HTTPResponse from the server."""

        # Initialize headers dictionary
        headers = {} if not headers else headers

        connection = httplib.HTTPConnection(host, port, timeout=100000)

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
        self.assertValidResponseHeaders(response)

        # Contains the response headers, body, etc
        return response

    def assertResponseSuccessful(self, response):
        """Asserts that a status code lies inside the 2xx range.

        :param response: :py:class:`httplib.HTTPResponse` to be
          verified to have a status code between 200 and 299.

        example::

            >>> self.assertResponseSuccessful(response, 203)
        """
        self.assertTrue(
            response.status >= 200 and response.status <= 299,
            'Status code %d is outside of the expected range (2xx)\n\n%s' %
            (response.status, response.body))

    def assertResponseStatus(self, response, expected_status):
        """Asserts a specific status code on the response.

        :param response: :py:class:`httplib.HTTPResponse`
        :param assert_status: The specific ``status`` result expected

        example::

            >>> self.assertResponseStatus(response, 203)
        """
        self.assertEqual(
            response.status,
            expected_status,
            'Status code %s is not %s, as expected)\n\n%s' %
            (response.status, expected_status, response.body))

    def assertValidResponseHeaders(self, response):
        """Ensures that response headers appear as expected."""
        self.assertIn('X-Auth-Token', response.getheader('Vary'))

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

        # make the original response body available, for convenience
        response.raw = response.body

        if response.body is not None and response.body.strip():
            # if a body is provided, a Content-Type is also expected
            header = response.getheader('Content-Type', None)
            self.assertIn(content_type, header)

            if content_type == 'json':
                response.body = jsonutils.loads(response.body)
            elif content_type == 'xml':
                response.body = etree.fromstring(response.body)

    def restful_request(self, method='GET', headers=None, body=None,
                        token=None, content_type=None, **kwargs):
        """Serializes/deserializes json/xml as request/response body.

        .. WARNING::

            * Existing Accept header will be overwritten.
            * Existing Content-Type header will be overwritten.

        """
        # Initialize headers dictionary
        headers = {} if not headers else headers

        if token is not None:
            headers['X-Auth-Token'] = token

        body = self._to_content_type(body, headers, content_type)

        # Perform the HTTP request/response
        response = self.request(method=method, headers=headers, body=body,
                                **kwargs)

        self._from_content_type(response, content_type)

        # we can save some code & improve coverage by always doing this
        if method != 'HEAD' and response.status >= 400:
            self.assertValidErrorResponse(response)

        # Contains the decoded response.body
        return response

    def _get_port(self, server):
        return server.socket_info['socket'][1]

    def _public_port(self):
        return self._get_port(self.public_server)

    def _admin_port(self):
        return self._get_port(self.admin_server)

    def public_request(self, port=None, **kwargs):
        kwargs['port'] = port or self._public_port()
        response = self.restful_request(**kwargs)
        self.assertValidResponseHeaders(response)
        return response

    def admin_request(self, port=None, **kwargs):
        kwargs['port'] = port or self._admin_port()
        response = self.restful_request(**kwargs)
        self.assertValidResponseHeaders(response)
        return response
