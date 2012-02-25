# Copyright (c) 2012 OpenStack, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import contextlib
import unittest
import webob
import nose

try:
    # NOTE(chmou): We don't want to force to have swift installed for
    # unit test so we skip it we have an ImportError.
    from keystone.middleware import swift_auth
    skip = False
except ImportError:
    skip = True


class FakeMemcache(object):

    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, timeout=0):
        self.store[key] = value
        return True

    def incr(self, key, timeout=0):
        self.store[key] = self.store.setdefault(key, 0) + 1
        return self.store[key]

    @contextlib.contextmanager
    def soft_lock(self, key, timeout=0, retries=5):
        yield True

    def delete(self, key):
        try:
            del self.store[key]
        except Exception:
            pass
        return True


class FakeApp(object):

    def __init__(self, status_headers_body_iter=None, acl=None, sync_key=None):
        self.calls = 0
        self.status_headers_body_iter = status_headers_body_iter
        if not self.status_headers_body_iter:
            self.status_headers_body_iter = iter([('404 Not Found', {}, '')])
        self.acl = acl
        self.sync_key = sync_key

    def __call__(self, env, start_response):
        self.calls += 1
        self.request = webob.Request.blank('', environ=env)
        if self.acl:
            self.request.acl = self.acl
        if self.sync_key:
            self.request.environ['swift_sync_key'] = self.sync_key
        if 'swift.authorize' in env:
            resp = env['swift.authorize'](self.request)
            if resp:
                return resp(env, start_response)
        status, headers, body = self.status_headers_body_iter.next()
        return webob.Response(status=status, headers=headers,
                              body=body)(env, start_response)


class FakeConn(object):

    def __init__(self, status_headers_body_iter=None):
        self.calls = 0
        self.status_headers_body_iter = status_headers_body_iter
        if not self.status_headers_body_iter:
            self.status_headers_body_iter = iter([('404 Not Found', {}, '')])

    def request(self, method, path, headers):
        self.calls += 1
        self.request_path = path
        self.status, self.headers, self.body = \
            self.status_headers_body_iter.next()
        self.status, self.reason = self.status.split(' ', 1)
        self.status = int(self.status)

    def getresponse(self):
        return self

    def read(self):
        body = self.body
        self.body = ''
        return body


class SwiftAuth(unittest.TestCase):

    def setUp(self):
        if skip:
            raise nose.SkipTest("no swift detected")
        self.auth = swift_auth
        self.test_auth = self.auth.filter_factory({})(FakeApp())

    def _make_request(self, path, **kwargs):
        req = webob.Request.blank(path, **kwargs)
        req.environ['swift.cache'] = FakeMemcache()
        return req

    def test_identity_status_denied(self):
        env = {
                'HTTP_X_IDENTITY_STATUS': 'Denied',
                }
        req = self._make_request('/v1/AUTH_acct')
        req.environ.update(env)
        resp = req.get_response(self.test_auth)
        self.assertEquals(resp.status_int, 401)

    def test_auth_deny_non_reseller_prefix(self):
        req = self._make_request('/v1/BLAH_account',
                                 headers={'X-Auth-Token': 'BLAH_t'})
        resp = req.get_response(self.test_auth)
        self.assertEquals(resp.status_int, 401)
        self.assertEquals(resp.environ['swift.authorize'],
                          self.test_auth.denied_response)

    def test_auth_deny_token_not_for_account(self):
        env = {
            'HTTP_X_IDENTITY_STATUS': 'Confirmed',
            'HTTP_X_USER': 'usr',
            'HTTP_X_TENANT_ID': '1',
            'HTTP_X_TENANT_NAME': 'acct',
            'HTTP_X_ROLE': 'AUTH_acct',
        }
        req = self._make_request('/v1/AUTH_1')
        req.environ.update(env)
        resp = req.get_response(self.test_auth)
        self.assertEquals(resp.status_int, 403)

    #NOTE(chmou): This should fail when we are going to add anonymous
    #access back.
    def test_default_forbidden(self):
        env = {
                'HTTP_X_IDENTITY_STATUS': 'Confirmed',
                'HTTP_X_USER': 'usr',
                'HTTP_X_TENANT_ID': '1',
                'HTTP_X_TENANT_NAME': 'acct',
                'HTTP_X_ROLE': '',
                }
        req = self._make_request('/v1/AUTH_acct')
        req.environ.update(env)
        resp = req.get_response(self.test_auth)
        self.assertEquals(resp.status_int, 403)

    def test_operator_roles(self):
        env = {
                'HTTP_X_IDENTITY_STATUS': 'Confirmed',
                'HTTP_X_USER': 'usr',
                'HTTP_X_TENANT_ID': '1',
                'HTTP_X_TENANT_NAME': 'acct',
                'HTTP_X_ROLE': 'owner',
                }
        self.test_auth = \
            self.auth.filter_factory({'operator_roles': 'owner'})(FakeApp())
        req = self._make_request('/v1/AUTH_1')
        req.environ.update(env)
        resp = req.get_response(self.test_auth)
        self.assertEquals(resp.status_int, 404)
        self.assertTrue('swift.authorize' in resp.environ)

    # NOTE(chmou): container-sync is buggy at this time readd it here
    # when it's fixed.
    def test_authorize_acl_referrer_access(self):
        env = {'keystone.identity':
                   {'roles': ['acct'],
                    'user': 'usr',
                    'tenant': ('1', 'acct')}}
        req = self._make_request('/v1/AUTH_1/c')
        req.environ.update(env)
        resp = self.test_auth.authorize(req)
        self.assertEquals(resp.status_int, 401)
        req = self._make_request('/v1/AUTH_1/c')
        req.acl = '.r:*,.rlistings'
        req.environ.update(env)
        self.assertEquals(self.test_auth.authorize(req), None)
        req = self._make_request('/v1/AUTH_1/c')
        req.environ.update(env)
        req.acl = '.r:*'  # No listings allowed
        resp = self.test_auth.authorize(req)
        self.assertEquals(resp.status_int, 401)
        req = self._make_request('/v1/AUTH_1/c')
        req.environ.update(env)
        req.acl = '.r:.example.com,.rlistings'
        resp = self.test_auth.authorize(req)
        self.assertEquals(resp.status_int, 401)
        req = self._make_request('/v1/AUTH_1/c')
        req.environ.update(env)
        req.referer = 'http://www.example.com/index.html'
        req.acl = '.r:.example.com,.rlistings'
        self.assertEquals(self.test_auth.authorize(req), None)

    def test_acl_tenant(self):
        env = {'keystone.identity':
                   {'roles': ['allowme'],
                    'user': 'usr',
                    'tenant': ('1', 'acct')}}
        req = self._make_request('/v1/AUTH_1/c')
        req.environ.update(env)
        req.acl = 'allowme'
        self.assertEquals(self.test_auth.authorize(req), None)

    def test_acl_tenant_user(self):
        env = {'keystone.identity':
                   {'roles': [''],
                    'user': 'usr',
                    'tenant': ('1', 'acct')}}
        req = self._make_request('/v1/AUTH_1/c')
        req.environ.update(env)
        req.acl = '1:usr'
        self.assertEquals(self.test_auth.authorize(req), None)

if __name__ == '__main__':
    unittest.main()
