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

from lxml import etree

from StringIO import StringIO
from webtest import TestApp
from webtest import TestRequest

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

    def setUp(self, *args, **kwargs):
        self._config_done = False
        super(RestfulTestCase, self).setUp(*args, **kwargs)
        self._public_app = None
        self._admin_app = None

    def tearDown(self):
        super(RestfulTestCase, self).tearDown()
        self._public_app = None
        self._admin_app = None

    def load_public_app(self):
        return TestApp(self.loadapp('keystone', 'main'))

    def load_admin_app(self):
        return TestApp(self.loadapp('keystone', 'admin'))

    @property
    def public_app(self):
        if not self._public_app:
            self._public_app = self.load_public_app()

        return self._public_app

    @property
    def admin_app(self):
        if not self._admin_app:
            self._admin_app = self.load_admin_app()

        return self._admin_app

    # def config(self, config_files):
    #     if not self._config_done:
    #         self._config_done = True
    #         test.TestCase.config(self, config_files)

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
            header = response.headers.get('content-type', None)
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

    def _request(self, kwargs):
        if kwargs.pop('convert', True):
            response = self.restful_request(**kwargs)
        else:
            response = self.request(**kwargs)

        self.assertValidResponseHeaders(response)
        return response

    def request(self, app=None, method='GET', path=None, headers=None,
                body=None, token=None, content_type=None, environ=None,
                expected_status=None, **kwargs):

        if not headers:
            headers = {}

        if not environ:
            environ = {}

        if token is not None:
            environ['HTTP_X_AUTH_TOKEN'] = str(token)

        environ['paste.throw_errors'] = True
        environ['REQUEST_METHOD'] = str(method)
        environ['REMOTE_ADDR'] = 'localhost'

        path = str(path)

        if body:
            environ['wsgi.input'] = StringIO(body)

        request = TestRequest.blank(path, environ)

        if body:
            request.content_length = len(body)

        for k, v in headers.iteritems():
            request.headers[str(k)] = str(v)

        response = app.do_request(request, status=expected_status,
                                  expect_errors=False)

        return response

    def admin_request(self, **kwargs):
        kwargs['app'] = self.admin_app
        return self._request(kwargs)

    def public_request(self, **kwargs):
        kwargs['app'] = self.public_app
        return self._request(kwargs)

    def assertValidResponseHeaders(self, response):
        """Ensures that response headers appear as expected."""
        self.assertIn('X-Auth-Token', response.headers.get('vary'))

    def assertResponseSuccessful(self, response):
        """Asserts that a status code lies inside the 2xx range.

        :param response: :py:class:`httplib.HTTPResponse` to be
          verified to have a status code between 200 and 299.

        example::

            >>> self.assertResponseSuccessful(response, 203)
        """
        self.assertTrue(
            response.status_code >= 200 and response.status_code <= 299,
            'Status code %d is outside of the expected range (2xx)\n\n%s' %
            (response.status_code, response.body))

    def assertResponseStatus(self, response, expected_status):
        """Asserts a specific status code on the response.

        :param response: :py:class:`httplib.HTTPResponse`
        :param assert_status: The specific ``status`` result expected

        example::

            >>> self.assertResponseStatus(response, 203)
        """
        self.assertEqual(
            response.status_code,
            expected_status,
            'Status code %s is not %s, as expected)\n\n%s' %
            (response.status_code, expected_status, response.body))
