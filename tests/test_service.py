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

import default_fixtures

from keystone import exception
from keystone import identity
from keystone import service
from keystone import test
from keystone.identity.backends import kvs as kvs_identity


def _build_user_auth(username, passwd, tenant):
    auth_json = {'passwordCredentials': {}}
    if username is not None:
        auth_json['passwordCredentials']['username'] = username
    if passwd is not None:
        auth_json['passwordCredentials']['password'] = passwd
    if tenant is not None:
        auth_json['tenantName'] = tenant
    return auth_json


class ServiceBadRequests(test.TestCase):
    def setUp(self):
        super(ServiceBadRequests, self).setUp()
        self.api = service.TokenController()


class TokenControllerTest(test.TestCase):
    def setUp(self):
        super(TokenControllerTest, self).setUp()
        self.identity_api = kvs_identity.Identity()
        self.load_fixtures(default_fixtures)
        self.api = service.TokenController()

    def assertEqualTokens(self, a, b):
        """Assert that two tokens are equal.

        Compare two tokens except for their ids. This also truncates
        the time in the comparison.
        """
        def normalize(token):
            token['access']['token']['id'] = 'dummy'
            # truncate to eliminate timing problems
            issued = token['access']['token']['issued_at']
            token['access']['token']['issued_at'] = issued[:-8]
            # truncate to eliminate timing problems
            expires = token['access']['token']['expires']
            token['access']['token']['expires'] = expires[:-3]
            return token
        return self.assertDictEqual(normalize(a), normalize(b))

    def test_unscoped_token(self):
        """Verify getting an unscoped token with password creds"""
        body_dict = _build_user_auth('FOO', 'foo2', None)
        unscoped_token = self.api.authenticate({}, body_dict)
        tenant = unscoped_token["access"]["token"].get("tenant", None)
        self.assertEqual(tenant, None)

    def test_auth_invalid_token(self):
        """Verify exception is raised if invalid token"""
        body_dict = {"token": {"id": "foobar"}}
        self.assertRaises(
            exception.Unauthorized,
            self.api.authenticate,
            {}, body_dict)

    def test_auth_invalid_user(self):
        """Verify exception is raised if invalid user"""
        body_dict = _build_user_auth("bazonk", "fingler", None)
        self.assertRaises(
            exception.Unauthorized,
            self.api.authenticate,
            {}, body_dict)

    def test_auth_valid_usar_invalid_password(self):
        """Verify exception is raised if invalid password"""
        body_dict = _build_user_auth("FOO", "fingler", None)
        self.assertRaises(
            exception.Unauthorized,
            self.api.authenticate,
            {}, body_dict)

    def test_auth_unscoped_token_no_tenant(self):
        """Verify getting an unscoped token with an unscoped token"""
        body_dict = _build_user_auth('FOO', 'foo2', None)
        unscoped_token = self.api.authenticate({}, body_dict)
        body_dict = {"token": unscoped_token["access"]["token"]}
        unscoped_token_2 = self.api.authenticate({}, body_dict)
        self.assertEqualTokens(unscoped_token, unscoped_token_2)

    def test_auth_unscoped_token_tenant(self):
        """Verify getting a token in a tenant with an unscoped token"""
        # Get an unscoped tenant
        body_dict = _build_user_auth('FOO', 'foo2', None)
        unscoped_token = self.api.authenticate({}, body_dict)
        # Get a token on BAR tenant using the unscoped tenant
        body_dict = {"token": unscoped_token["access"]["token"],
                     "tenantName": "BAR"}
        scoped_token = self.api.authenticate({}, body_dict)

        tenant = scoped_token["access"]["token"]["tenant"]
        self.assertEquals(tenant["id"], self.tenant_bar['id'])

    def test_no_external_auth(self):
        """Verify that _authenticate_external() raises exception if
        not applicable"""
        self.assertRaises(
            service.ExternalAuthNotApplicable,
            self.api._authenticate_external,
            {}, {})

    def test_no_token_in_auth(self):
        """Verity that _authenticate_token() raises exception if no token"""
        self.assertRaises(
            exception.ValidationError,
            self.api._authenticate_token,
            None, {})

    def test_no_credentials_in_auth(self):
        """Verity that _authenticate_local() raises exception if no creds"""
        self.assertRaises(
            exception.ValidationError,
            self.api._authenticate_local,
            None, {})

    def test_authenticate_blank_password_credentials(self):
        """Verify sending empty json dict as passwordCredentials raises the
        right exception."""
        body_dict = {'passwordCredentials': {}, 'tenantName': 'demo'}
        self.assertRaises(exception.ValidationError, self.api.authenticate,
                          {}, body_dict)

    def test_authenticate_no_username(self):
        """Verify skipping username raises the right exception."""
        body_dict = {'passwordCredentials': {'password': 'pass'},
                     'tenantName': 'demo'}
        self.assertRaises(exception.ValidationError, self.api.authenticate,
                          {}, body_dict)

    def test_authenticate_no_password(self):
        """Verify skipping password raises the right exception."""
        body_dict = {'passwordCredentials': {'username': 'user1'},
                     'tenantName': 'demo'}
        self.assertRaises(exception.ValidationError, self.api.authenticate,
                          {}, body_dict)

    def test_authenticate_blank_request_body(self):
        """Verify sending empty json dict raises the right exception."""
        self.assertRaises(exception.ValidationError, self.api.authenticate,
                          {}, {})

    def test_authenticate_blank_auth(self):
        """Verify sending blank 'auth' raises the right exception."""
        self.assertRaises(exception.ValidationError, self.api.authenticate,
                          {}, {'auth': {}})

    def test_authenticate_invalid_auth_content(self):
        """Verify sending invalid 'auth' raises the right exception."""
        self.assertRaises(exception.ValidationError, self.api.authenticate,
                          {}, {'auth': 'abcd'})

    def test_unscoped_remote_authn(self):
        """Verify getting an unscoped token with external authn"""
        local_token = self.api.authenticate(
            {},
            _build_user_auth('FOO', 'foo2', None))
        remote_token = self.api.authenticate(
            {'REMOTE_USER': 'FOO'},
            _build_user_auth('FOO', 'nosir', None))
        self.assertEqualTokens(local_token, remote_token)

    def test_unscoped_remote_authn_jsonless(self):
        """Verify that external auth with invalid request fails"""
        self.assertRaises(
            exception.ValidationError,
            self.api.authenticate,
            {'REMOTE_USER': 'FOO'},
            None)

    def test_scoped_remote_authn(self):
        """Verify getting a token with external authn"""
        local_token = self.api.authenticate(
            {},
            _build_user_auth('FOO', 'foo2', 'BAR'))
        remote_token = self.api.authenticate(
            {'REMOTE_USER': 'FOO'},
            _build_user_auth('FOO', 'nosir', 'BAR'))
        self.assertEqualTokens(local_token, remote_token)

    def test_scoped_nometa_remote_authn(self):
        """Verify getting a token with external authn and no metadata"""
        local_token = self.api.authenticate(
            {},
            _build_user_auth('NO_META', 'no_meta2', 'BAZ'))
        remote_token = self.api.authenticate(
            {'REMOTE_USER': 'NO_META'},
            _build_user_auth('NO_META', 'nosir', 'BAZ'))
        self.assertEqualTokens(local_token, remote_token)

    def test_scoped_remote_authn_invalid_user(self):
        """Verify that external auth with invalid user fails"""
        self.assertRaises(
            exception.Unauthorized,
            self.api.authenticate,
            {'REMOTE_USER': 'FOOZBALL'},
            _build_user_auth('FOO', 'nosir', 'BAR'))
