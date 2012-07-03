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

import string
import webob
import datetime
import iso8601
import webob

from keystone.middleware import auth_token
from keystone.openstack.common import jsonutils
from keystone import config
from keystone import test

DEFAULT_UUID_TOKEN = "123456789ABCDEF123456789ABCDEF"

DEFAULT_SIGNED_TOKEN = string.replace(
    """MIIG7QYJKoZIhvcNAQcCoIIG3jCCBtoCAQExCTAHBgUrDgMCGjCCBc4GCSqGSIb3
DQEHAaCCBb8EggW7eyJhY2Nlc3MiOiB7InNlcnZpY2VDYXRhbG9nIjogW3siZW5k
cG9pbnRzIjogW3siYWRtaW5VUkwiOiAiaHR0cDovLzEyNy4wLjAuMTo4Nzc2L3Yx
LzY0YjZmM2ZiY2M1MzQzNWU4YTYwZmNmODliYjY2MTdhIiwgInJlZ2lvbiI6ICJy
ZWdpb25PbmUiLCAiaW50ZXJuYWxVUkwiOiAiaHR0cDovLzEyNy4wLjAuMTo4Nzc2
L3YxLzY0YjZmM2ZiY2M1MzQzNWU4YTYwZmNmODliYjY2MTdhIiwgInB1YmxpY1VS
TCI6ICJodHRwOi8vMTI3LjAuMC4xOjg3NzYvdjEvNjRiNmYzZmJjYzUzNDM1ZThh
NjBmY2Y4OWJiNjYxN2EifV0sICJlbmRwb2ludHNfbGlua3MiOiBbXSwgInR5cGUi
OiAidm9sdW1lIiwgIm5hbWUiOiAidm9sdW1lIn0sIHsiZW5kcG9pbnRzIjogW3si
YWRtaW5VUkwiOiAiaHR0cDovLzEyNy4wLjAuMTo5MjkyL3YxIiwgInJlZ2lvbiI6
ICJyZWdpb25PbmUiLCAiaW50ZXJuYWxVUkwiOiAiaHR0cDovLzEyNy4wLjAuMTo5
MjkyL3YxIiwgInB1YmxpY1VSTCI6ICJodHRwOi8vMTI3LjAuMC4xOjkyOTIvdjEi
fV0sICJlbmRwb2ludHNfbGlua3MiOiBbXSwgInR5cGUiOiAiaW1hZ2UiLCAibmFt
ZSI6ICJnbGFuY2UifSwgeyJlbmRwb2ludHMiOiBbeyJhZG1pblVSTCI6ICJodHRw
Oi8vMTI3LjAuMC4xOjg3NzQvdjEuMS82NGI2ZjNmYmNjNTM0MzVlOGE2MGZjZjg5
YmI2NjE3YSIsICJyZWdpb24iOiAicmVnaW9uT25lIiwgImludGVybmFsVVJMIjog
Imh0dHA6Ly8xMjcuMC4wLjE6ODc3NC92MS4xLzY0YjZmM2ZiY2M1MzQzNWU4YTYw
ZmNmODliYjY2MTdhIiwgInB1YmxpY1VSTCI6ICJodHRwOi8vMTI3LjAuMC4xOjg3
NzQvdjEuMS82NGI2ZjNmYmNjNTM0MzVlOGE2MGZjZjg5YmI2NjE3YSJ9XSwgImVu
ZHBvaW50c19saW5rcyI6IFtdLCAidHlwZSI6ICJjb21wdXRlIiwgIm5hbWUiOiAi
bm92YSJ9LCB7ImVuZHBvaW50cyI6IFt7ImFkbWluVVJMIjogImh0dHA6Ly8xMjcu
MC4wLjE6MzUzNTcvdjIuMCIsICJyZWdpb24iOiAiUmVnaW9uT25lIiwgImludGVy
bmFsVVJMIjogImh0dHA6Ly8xMjcuMC4wLjE6MzUzNTcvdjIuMCIsICJwdWJsaWNV
UkwiOiAiaHR0cDovLzEyNy4wLjAuMTo1MDAwL3YyLjAifV0sICJlbmRwb2ludHNf
bGlua3MiOiBbXSwgInR5cGUiOiAiaWRlbnRpdHkiLCAibmFtZSI6ICJrZXlzdG9u
ZSJ9XSwidG9rZW4iOiB7ImV4cGlyZXMiOiAiMjAxMi0wNi0wMlQxNDo0NzozNFoi
LCAiaWQiOiAicGxhY2Vob2xkZXIiLCAidGVuYW50IjogeyJlbmFibGVkIjogdHJ1
ZSwgImRlc2NyaXB0aW9uIjogbnVsbCwgIm5hbWUiOiAidGVuYW50X25hbWUxIiwg
ImlkIjogInRlbmFudF9pZDEifX0sICJ1c2VyIjogeyJ1c2VybmFtZSI6ICJ1c2Vy
X25hbWUxIiwgInJvbGVzX2xpbmtzIjogWyJyb2xlMSIsInJvbGUyIl0sICJpZCI6
ICJ1c2VyX2lkMSIsICJyb2xlcyI6IFt7Im5hbWUiOiAicm9sZTEifSwgeyJuYW1l
IjogInJvbGUyIn1dLCAibmFtZSI6ICJ1c2VyX25hbWUxIn19fQ0KMYH3MIH0AgEB
MFQwTzEVMBMGA1UEChMMUmVkIEhhdCwgSW5jMREwDwYDVQQHEwhXZXN0Zm9yZDEW
MBQGA1UECBMNTWFzc2FjaHVzZXR0czELMAkGA1UEBhMCVVMCAQEwBwYFKw4DAhow
DQYJKoZIhvcNAQEBBQAEgYAD6hPEpc/0wHe3rYDBFec52h7gxdbrTNEN7jmwdFto
xw0QnucmCREh9IUikJ2ob0c0uUC6cmNPajD9aFkGWhvNswNH2W2BYzUiC3CHM7U0
7nsIe3OOatqyUAyoQUhHZnIAx1tOgdPBVflnrtdIV1vkdqxednlJZ52Hxob2PP3h
xg==""", "\n", "")


INVALID_SIGNED_TOKEN = string.replace(
    """AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB
CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC
DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD
EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE
FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
0000000000000000000000000000000000000000000000000000000000000000
1111111111111111111111111111111111111111111111111111111111111111
2222222222222222222222222222222222222222222222222222222222222222
3333333333333333333333333333333333333333333333333333333333333333
4444444444444444444444444444444444444444444444444444444444444444
5555555555555555555555555555555555555555555555555555555555555555
6666666666666666666666666666666666666666666666666666666666666666
7777777777777777777777777777777777777777777777777777777777777777
8888888888888888888888888888888888888888888888888888888888888888
9999999999999999999999999999999999999999999999999999999999999999
0000000000000000000000000000000000000000000000000000000000000000
xg==""", "\n", "")

# JSON responses keyed by token ID
TOKEN_RESPONSES = {
    DEFAULT_UUID_TOKEN: {
        'access': {
            'token': {
                'id': DEFAULT_UUID_TOKEN,
                'tenant': {
                    'id': 'tenant_id1',
                    'name': 'tenant_name1',
                },
            },
            'user': {
                'id': 'user_id1',
                'name': 'user_name1',
                'roles': [
                    {'name': 'role1'},
                    {'name': 'role2'},
                ],
            },
            'serviceCatalog': {}
        },
    },
    DEFAULT_SIGNED_TOKEN: {
        'access': {
            'token': {
                'id': DEFAULT_SIGNED_TOKEN,
            },
            'user': {
                'id': 'user_id1',
                'name': 'user_name1',
                'tenantId': 'tenant_id1',
                'tenantName': 'tenant_name1',
                'roles': [
                    {'name': 'role1'},
                    {'name': 'role2'},
                ],
            },
        },
    },
    'valid-diablo-token': {
        'access': {
            'token': {
                'id': 'valid-diablo-token',
                'tenantId': 'tenant_id1',
            },
            'user': {
                'id': 'user_id1',
                'name': 'user_name1',
                'roles': [
                    {'name': 'role1'},
                    {'name': 'role2'},
                ],
            },
        },
    },
    'unscoped-token': {
        'access': {
            'token': {
                'id': 'unscoped-token',
            },
            'user': {
                'id': 'user_id1',
                'name': 'user_name1',
                'roles': [
                    {'name': 'role1'},
                    {'name': 'role2'},
                ],
            },
        },
    },
    'valid-token-no-service-catalog': {
        'access': {
            'token': {
                'id': 'valid-token',
                'tenant': {
                    'id': 'tenant_id1',
                    'name': 'tenant_name1',
                },
            },
            'user': {
                'id': 'user_id1',
                'name': 'user_name1',
                'roles': [
                    {'name': 'role1'},
                    {'name': 'role2'},
                ],
            }
        },
    },
}


class FakeMemcache(object):
    def __init__(self):
        self.set_key = None
        self.set_value = None
        self.token_expiration = None

    def get(self, key):
        data = TOKEN_RESPONSES[DEFAULT_SIGNED_TOKEN].copy()
        if not data or key != "tokens/%s" % (data['access']['token']['id']):
            return
        if not self.token_expiration:
            dt = datetime.datetime.now() + datetime.timedelta(minutes=5)
            self.token_expiration = dt.strftime("%s")
        dt = datetime.datetime.now() + datetime.timedelta(hours=24)
        ks_expires = dt.isoformat()
        data['access']['token']['expires'] = ks_expires
        return (data, str(self.token_expiration))

    def set(self, key, value, time=None):
        self.set_value = value
        self.set_key = key


class FakeHTTPResponse(object):
    def __init__(self, status, body):
        self.status = status
        self.body = body

    def read(self):
        return self.body


class FakeHTTPConnection(object):

    last_requested_url = ''

    def __init__(self, *args):
        pass

    def request(self, method, path, **kwargs):
        """Fakes out several http responses.

        If a POST request is made, we assume the calling code is trying
        to get a new admin token.

        If a GET request is made to validate a token, return success
        if the token is 'token1'. If a different token is provided, return
        a 404, indicating an unknown (therefore unauthorized) token.

        """
        FakeHTTPConnection.last_requested_url = path
        if method == 'POST':
            status = 200
            body = jsonutils.dumps({
                'access': {
                    'token': {'id': 'admin_token2'},
                },
            })

        else:
            token_id = path.rsplit('/', 1)[1]
            if token_id in TOKEN_RESPONSES.keys():
                status = 200
                body = jsonutils.dumps(TOKEN_RESPONSES[token_id])
            else:
                status = 404
                body = str()

        self.resp = FakeHTTPResponse(status, body)

    def getresponse(self):
        return self.resp

    def close(self):
        pass


class FakeApp(object):
    """This represents a WSGI app protected by the auth_token middleware."""
    def __init__(self, expected_env=None):
        expected_env = expected_env or {}
        self.expected_env = {
            'HTTP_X_IDENTITY_STATUS': 'Confirmed',
            'HTTP_X_TENANT_ID': 'tenant_id1',
            'HTTP_X_TENANT_NAME': 'tenant_name1',
            'HTTP_X_USER_ID': 'user_id1',
            'HTTP_X_USER_NAME': 'user_name1',
            'HTTP_X_ROLES': 'role1,role2',
            'HTTP_X_USER': 'user_name1',  # deprecated (diablo-compat)
            'HTTP_X_TENANT': 'tenant_name1',  # deprecated (diablo-compat)
            'HTTP_X_ROLE': 'role1,role2',  # deprecated (diablo-compat)
        }
        self.expected_env.update(expected_env)

    def __call__(self, env, start_response):
        for k, v in self.expected_env.items():
            assert env[k] == v, '%s != %s' % (env[k], v)

        resp = webob.Response()
        resp.body = 'SUCCESS'
        return resp(env, start_response)


class BaseAuthTokenMiddlewareTest(test.TestCase):

    def setUp(self, expected_env=None):
        expected_env = expected_env or {}

        conf = {
            'admin_token': 'admin_token1',
            'auth_host': 'keystone.example.com',
            'auth_port': 1234,
            'auth_admin_prefix': '/testadmin',
            'signing_dir': 'signing'
        }

        self.middleware = auth_token.AuthProtocol(FakeApp(expected_env), conf)
        self.middleware.http_client_class = FakeHTTPConnection
        self.middleware._iso8601 = iso8601

        self.response_status = None
        self.response_headers = None
        super(BaseAuthTokenMiddlewareTest, self).setUp()

    def start_fake_response(self, status, headers):
        self.response_status = int(status.split(' ', 1)[0])
        self.response_headers = dict(headers)


class DiabloAuthTokenMiddlewareTest(BaseAuthTokenMiddlewareTest):
    """Auth Token middleware should understand Diablo keystone responses."""
    def setUp(self):
        # pre-diablo only had Tenant ID, which was also the Name
        expected_env = {
            'HTTP_X_TENANT_ID': 'tenant_id1',
            'HTTP_X_TENANT_NAME': 'tenant_id1',
            # now deprecated (diablo-compat)
            'HTTP_X_TENANT': 'tenant_id1',
        }
        super(DiabloAuthTokenMiddlewareTest, self).setUp(expected_env)


class AuthTokenMiddlewareTest(BaseAuthTokenMiddlewareTest):

    def test_valid_uuid_request(self):
        req = webob.Request.blank('/')
        req.headers['X-Auth-Token'] = DEFAULT_UUID_TOKEN
        body = self.middleware(req.environ, self.start_fake_response)
        self.assertEqual("/testadmin/v2.0/tokens/%s" % DEFAULT_UUID_TOKEN,
                         FakeHTTPConnection.last_requested_url)
        self.assertEqual(self.response_status, 200)
        catalog = req.headers.get('X-Service-Catalog')
        self.assertTrue(req.headers.get('X-Service-Catalog'))
        self.assertEqual(body, ['SUCCESS'])

    def test_valid_signed_request(self):
        #ensure that signed requests do not generate HTTP traffic
        FakeHTTPConnection.last_requested_url = ''
        req = webob.Request.blank('/')
        req.headers['X-Auth-Token'] = DEFAULT_SIGNED_TOKEN
        body = self.middleware(req.environ, self.start_fake_response)
        self.assertEqual(self.middleware.conf['auth_admin_prefix'],
                         "/testadmin")
        self.assertEqual('', FakeHTTPConnection.last_requested_url)
        self.assertEqual(self.response_status, 200)
        catalog = req.headers.get('X-Service-Catalog')
        self.assertTrue(req.headers.get('X-Service-Catalog'))
        self.assertEqual(body, ['SUCCESS'])

    def test_default_tenant_token(self):
        """Unscoped requests with a default tenant should "auto-scope."

        The implied scope is the user's tenant ID.

        """

        req = webob.Request.blank('/')
        req.headers['X-Auth-Token'] = DEFAULT_SIGNED_TOKEN
        body = self.middleware(req.environ, self.start_fake_response)
        self.assertEqual(self.response_status, 200)
        self.assertEqual(body, ['SUCCESS'])

    def test_unscoped_token(self):
        """Unscoped requests with no default tenant ID should be rejected."""
        req = webob.Request.blank('/')
        req.headers['X-Auth-Token'] = 'unscoped-token'
        self.middleware(req.environ, self.start_fake_response)
        self.assertEqual(self.response_status, 401)
        self.assertEqual(self.response_headers['WWW-Authenticate'],
                         'Keystone uri=\'https://keystone.example.com:1234\'')

    def test_request_invalid_uuid_token(self):
        req = webob.Request.blank('/')
        req.headers['X-Auth-Token'] = 'invalid-token'
        self.middleware(req.environ, self.start_fake_response)
        self.assertEqual(self.response_status, 401)
        self.assertEqual(self.response_headers['WWW-Authenticate'],
                         'Keystone uri=\'https://keystone.example.com:1234\'')

    def test_request_invalid_signed_token(self):
        req = webob.Request.blank('/')
        req.headers['X-Auth-Token'] = INVALID_SIGNED_TOKEN
        self.middleware(req.environ, self.start_fake_response)
        self.assertEqual(self.response_status, 401)
        self.assertEqual(self.response_headers['WWW-Authenticate'],
                         'Keystone uri=\'https://keystone.example.com:1234\'')

    def test_request_no_token(self):
        req = webob.Request.blank('/')
        self.middleware(req.environ, self.start_fake_response)
        self.assertEqual(self.response_status, 401)
        self.assertEqual(self.response_headers['WWW-Authenticate'],
                         'Keystone uri=\'https://keystone.example.com:1234\'')

    def test_request_blank_token(self):
        req = webob.Request.blank('/')
        req.headers['X-Auth-Token'] = ''
        self.middleware(req.environ, self.start_fake_response)
        self.assertEqual(self.response_status, 401)
        self.assertEqual(self.response_headers['WWW-Authenticate'],
                         'Keystone uri=\'https://keystone.example.com:1234\'')

    def test_memcache(self):
        req = webob.Request.blank('/')
        req.headers['X-Auth-Token'] = DEFAULT_SIGNED_TOKEN
        self.middleware._cache = FakeMemcache()
        self.middleware(req.environ, self.start_fake_response)
        self.assertEqual(self.middleware._cache.set_value, None)

    def test_memcache_set_invalid(self):
        req = webob.Request.blank('/')
        req.headers['X-Auth-Token'] = 'invalid-token'
        self.middleware._cache = FakeMemcache()
        self.middleware(req.environ, self.start_fake_response)
        self.assertEqual(self.middleware._cache.set_value, "invalid")

    def test_memcache_set_expired(self):
        req = webob.Request.blank('/')
        req.headers['X-Auth-Token'] = DEFAULT_SIGNED_TOKEN
        self.middleware._cache = FakeMemcache()
        expired = datetime.datetime.now() - datetime.timedelta(minutes=1)
        self.middleware._cache.token_expiration = float(expired.strftime("%s"))
        self.middleware(req.environ, self.start_fake_response)
        self.assertEqual(len(self.middleware._cache.set_value), 2)

    def test_nomemcache(self):
        self.disable_module('memcache')

        conf = {
            'admin_token': 'admin_token1',
            'auth_host': 'keystone.example.com',
            'auth_port': 1234,
            'memcache_servers': 'localhost:11211',
        }

        auth_token.AuthProtocol(FakeApp(), conf)

    def test_request_prevent_service_catalog_injection(self):
        req = webob.Request.blank('/')
        req.headers['X-Service-Catalog'] = '[]'
        req.headers['X-Auth-Token'] = 'valid-token-no-service-catalog'
        body = self.middleware(req.environ, self.start_fake_response)
        self.assertEqual(self.response_status, 200)
        self.assertFalse(req.headers.get('X-Service-Catalog'))
        self.assertEqual(body, ['SUCCESS'])


if __name__ == '__main__':
    import unittest
    unittest.main()
