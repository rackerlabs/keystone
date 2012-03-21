# Copyright 2012 Internap Network Services Corp.
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

import unittest2 as unittest
from webob import Request, exc

from swiftstone import authz as auth
from swiftstone.identity import Identity

from utils import FakeApp


class TestAuthz(unittest.TestCase):

    def setUp(self):
        self.test_auth = auth.filter_factory({})(FakeApp())

    @property
    def identity(self):
        return Identity('AUTH_tenant_id', 'tenant_id', 'user', 'roles')

    def _make_request(self, path=None, headers=None, cache=None, **kwargs):
        if not path:
            path = '/v1/a/b/c'
        req = Request.blank(path, headers=headers, **kwargs)
        return req

    def test_request_succeeds_for_anoymous_access(self):
        headers = {'X_IDENTITY_STATUS': Identity.INVALID}
        req = self._make_request(headers=headers)
        req.acl = '.r:*'
        response_iter = iter([('200 OK', {}, '')])
        test_auth = auth.filter_factory({})(FakeApp(response_iter))
        resp = req.get_response(test_auth)
        self.assertEqual(resp.status_int, 200)

    def test_request_returns_401_for_unauthorized_anonymous_access(self):
        req = self._make_request(
            headers={'X_IDENTITY_STATUS': Identity.INVALID})
        resp = req.get_response(self.test_auth)
        self.assertEqual(resp.status_int, 401)

    def test_request_succeeds_for_confirmed_identity(self):
        identity = self.identity
        # Ensure the user is identified as admin
        identity.user = identity.tenant_name
        headers = identity.to_headers()
        prefix = 'HTTP_'
        headers = dict((x[len(prefix):], y) for x, y in headers.iteritems())
        headers['X_IDENTITY_STATUS'] = Identity.CONFIRMED
        path = '/v1/%s/b/c' % identity.tenant_id
        req = self._make_request(path, headers)
        response_iter = iter([('200 OK', {}, '')])
        test_auth = auth.filter_factory({'is_admin': '1'})(
            FakeApp(response_iter))
        resp = req.get_response(test_auth)
        self.assertEqual(resp.status_int, 200)

    def check_authenticate(self, account=None, identity=None, headers=None,
                           exception=None, acl=None, environ=None):
        if not identity:
            identity = self.identity
        if not account:
            account = identity.tenant_id
        path = '/v1/%s/c' % account
        remote_user = (identity.tenant_id, identity.tenant_name)
        env = {'swiftstone.identity': identity, 'REMOTE_USER': remote_user}
        if environ:
            env.update(environ)
        req = self._make_request(path, headers=headers, environ=env)
        req.acl = acl
        result = self.test_auth.authorize(req)
        if exception:
            self.assertIsInstance(result, exception)
        else:
            self.assertIsNone(result)

    def test_authorize_fails_for_tenant_mismatch(self):
        self.check_authenticate(account='a', exception=exc.HTTPForbidden)

    def test_authorize_fails(self):
        self.check_authenticate(exception=exc.HTTPForbidden)

    def test_authorize_succeeds_as_owner_for_operator_role(self):
        identity = self.identity
        identity.roles = ['admin']
        self.check_authenticate(identity=identity)

    def test_authorize_succeeds_as_owner_for_tenant_owner_match(self):
        identity = self.identity
        identity.user = identity.tenant_name
        self.test_auth.is_admin = True
        self.check_authenticate(identity=identity)

    def test_authorize_succeeds_for_container_sync(self):
        environ = {'swift_sync_key': 'foo', 'REMOTE_ADDR': '127.0.0.1'}
        headers = {'x-container-sync-key': 'foo', 'x-timestamp': None}
        self.check_authenticate(environ=environ, headers=headers)

    def test_authorize_fails_for_referrer_without_rlistings(self):
        environ = {'HTTP_REFERER': 'http://foobar'}
        self.check_authenticate(acl='.r:foobar', environ=environ,
                                exception=exc.HTTPForbidden)

    def test_authorize_succeeds_for_referrer_with_rlistings(self):
        environ = {'HTTP_REFERER': 'http://foobar'}
        self.check_authenticate(acl='.r:foobar,.rlistings', environ=environ)

    def test_authorize_succeeds_for_tenant_user_in_groups(self):
        identity = self.identity
        self.check_authenticate(identity=identity, acl=identity.tenant_user)

    def test_authorize_succeeds_for_user_role_in_groups(self):
        self.check_authenticate(identity=self.identity, acl='roles')
