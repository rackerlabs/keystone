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

import base64
import uuid

import webob

from keystone.common import dependency
from keystone import config
from keystone import exception
from keystone import middleware
from keystone.middleware import basic_auth
from keystone.openstack.common import jsonutils
from keystone import tests


CONF = config.CONF


def make_request(**kwargs):
    accept = kwargs.pop('accept', None)
    method = kwargs.pop('method', 'GET')
    body = kwargs.pop('body', None)
    req = webob.Request.blank('/', **kwargs)
    req.method = method
    if body is not None:
        req.body = body
    if accept is not None:
        req.accept = accept
    return req


def make_response(**kwargs):
    body = kwargs.pop('body', None)
    return webob.Response(body)


class TokenAuthMiddlewareTest(tests.TestCase):
    def test_request(self):
        req = make_request()
        req.headers[middleware.AUTH_TOKEN_HEADER] = 'MAGIC'
        middleware.TokenAuthMiddleware(None).process_request(req)
        context = req.environ[middleware.CONTEXT_ENV]
        self.assertEqual('MAGIC', context['token_id'])


class AdminTokenAuthMiddlewareTest(tests.TestCase):
    def test_request_admin(self):
        req = make_request()
        req.headers[middleware.AUTH_TOKEN_HEADER] = CONF.admin_token
        middleware.AdminTokenAuthMiddleware(None).process_request(req)
        context = req.environ[middleware.CONTEXT_ENV]
        self.assertTrue(context['is_admin'])

    def test_request_non_admin(self):
        req = make_request()
        req.headers[middleware.AUTH_TOKEN_HEADER] = 'NOT-ADMIN'
        middleware.AdminTokenAuthMiddleware(None).process_request(req)
        context = req.environ[middleware.CONTEXT_ENV]
        self.assertFalse(context['is_admin'])


class PostParamsMiddlewareTest(tests.TestCase):
    def test_request_with_params(self):
        req = make_request(body="arg1=one", method='POST')
        middleware.PostParamsMiddleware(None).process_request(req)
        params = req.environ[middleware.PARAMS_ENV]
        self.assertEqual({"arg1": "one"}, params)


class JsonBodyMiddlewareTest(tests.TestCase):
    def test_request_with_params(self):
        req = make_request(body='{"arg1": "one", "arg2": ["a"]}',
                           content_type='application/json',
                           method='POST')
        middleware.JsonBodyMiddleware(None).process_request(req)
        params = req.environ[middleware.PARAMS_ENV]
        self.assertEqual({"arg1": "one", "arg2": ["a"]}, params)

    def test_malformed_json(self):
        req = make_request(body='{"arg1": "on',
                           content_type='application/json',
                           method='POST')
        resp = middleware.JsonBodyMiddleware(None).process_request(req)
        self.assertEqual(400, resp.status_int)

    def test_no_content_type(self):
        req = make_request(body='{"arg1": "one", "arg2": ["a"]}',
                           method='POST')
        middleware.JsonBodyMiddleware(None).process_request(req)
        params = req.environ[middleware.PARAMS_ENV]
        self.assertEqual({"arg1": "one", "arg2": ["a"]}, params)

    def test_unrecognized_content_type(self):
        req = make_request(body='{"arg1": "one", "arg2": ["a"]}',
                           content_type='text/plain',
                           method='POST')
        resp = middleware.JsonBodyMiddleware(None).process_request(req)
        self.assertEqual(400, resp.status_int)

    def test_unrecognized_content_type_without_body(self):
        req = make_request(content_type='text/plain',
                           method='GET')
        middleware.JsonBodyMiddleware(None).process_request(req)
        params = req.environ.get(middleware.PARAMS_ENV, {})
        self.assertEqual({}, params)


class XmlBodyMiddlewareTest(tests.TestCase):
    def test_client_wants_xml_back(self):
        """Clients requesting XML should get what they ask for."""
        body = '{"container": {"attribute": "value"}}'
        req = make_request(body=body, method='POST', accept='application/xml')
        middleware.XmlBodyMiddleware(None).process_request(req)
        resp = make_response(body=body)
        middleware.XmlBodyMiddleware(None).process_response(req, resp)
        self.assertEqual('application/xml', resp.content_type)

    def test_client_wants_json_back(self):
        """Clients requesting JSON should definitely not get XML back."""
        body = '{"container": {"attribute": "value"}}'
        req = make_request(body=body, method='POST', accept='application/json')
        middleware.XmlBodyMiddleware(None).process_request(req)
        resp = make_response(body=body)
        middleware.XmlBodyMiddleware(None).process_response(req, resp)
        self.assertNotIn('application/xml', resp.content_type)

    def test_client_fails_to_specify_accept(self):
        """If client does not specify an Accept header, default to JSON."""
        body = '{"container": {"attribute": "value"}}'
        req = make_request(body=body, method='POST')
        middleware.XmlBodyMiddleware(None).process_request(req)
        resp = make_response(body=body)
        middleware.XmlBodyMiddleware(None).process_response(req, resp)
        self.assertNotIn('application/xml', resp.content_type)

    def test_xml_replaced_by_json(self):
        """XML requests should be replaced by JSON requests."""
        req = make_request(
            body='<container><element attribute="value" /></container>',
            content_type='application/xml',
            method='POST')
        middleware.XmlBodyMiddleware(None).process_request(req)
        self.assertEqual('application/json', req.content_type)
        self.assertTrue(jsonutils.loads(req.body))

    def test_json_unnaffected(self):
        """JSON-only requests should be unaffected by the XML middleware."""
        content_type = 'application/json'
        body = '{"container": {"attribute": "value"}}'
        req = make_request(body=body, content_type=content_type, method='POST')
        middleware.XmlBodyMiddleware(None).process_request(req)
        self.assertEqual(body, req.body)
        self.assertEqual(content_type, req.content_type)


@dependency.provider('identity_api')
class MockIdentity(object):
    _users = dict()

    def valid_user(self, user_id, password):
        self._users[user_id] = password

    def authenticate(self, context, user_id, password, domain_scope=None):
        test_user_password = self._users.get(user_id)
        if test_user_password is None:
            raise exception.UserNotFound(user_id=user_id)
        if test_user_password != password:
            raise exception.UserNotFound(user_id=user_id)


class BasicAuthMiddlewareTest(tests.TestCase):
    def setUp(self):
        super(BasicAuthMiddlewareTest, self).setUp()
        self.mock_id = MockIdentity()
        self.username = uuid.uuid4().hex
        self.password = uuid.uuid4().hex
        self.mock_id.valid_user(self.username, self.password)

    def make_request(self, username, password):
        req = make_request(body='{}',
                           content_type='application/json',
                           method='POST')
        encoded_creds = base64.b64encode(username + ':' + password)
        req.headers['Authorization'] = 'Basic ' + encoded_creds
        return req

    def test_basic_auth_success(self):
        req = self.make_request(self.username, self.password)
        basic_auth.BasicAuthMiddleware(None).process_request(req)
        self.assertEqual(self.username, req.environ['REMOTE_USER'])

    def test_basic_auth_bad_password(self):
        invalid_password = uuid.uuid4().hex
        req = self.make_request(self.username, invalid_password)
        basic_auth_middleware = basic_auth.BasicAuthMiddleware(None)
        self.assertRaises(exception.UserNotFound,
                          basic_auth_middleware.process_request,
                          req)

    def test_basic_auth_incorrect_user(self):
        invalid_user = uuid.uuid4().hex
        req = self.make_request(invalid_user, self.password)
        basic_auth_middleware = basic_auth.BasicAuthMiddleware(None)
        self.assertRaises(exception.UserNotFound,
                          basic_auth_middleware.process_request,
                          req)

    def test_invalid_auth_header(self):
        req = self.make_request(self.username, self.password)
        req.headers['Authorization'] = 'abcd'
        basic_auth_middleware = basic_auth.BasicAuthMiddleware(None)
        self.assertRaises(exception.Unauthorized,
                          basic_auth_middleware.process_request,
                          req)

    def test_invalid_encoded_creds_auth_header(self):
        req = self.make_request(self.username, self.password)
        req.headers['Authorization'] = 'Basic ' + base64.b64encode('abcd')
        basic_auth_middleware = basic_auth.BasicAuthMiddleware(None)
        self.assertRaises(exception.Unauthorized,
                          basic_auth_middleware.process_request,
                          req)

    def test_invalid_scheme_in_auth_header(self):
        req = self.make_request(self.username, self.password)
        req.headers['Authorization'] = 'Complex ' + base64.b64encode(':abcd')
        basic_auth_middleware = basic_auth.BasicAuthMiddleware(None)
        self.assertRaises(exception.Unauthorized,
                          basic_auth_middleware.process_request,
                          req)
