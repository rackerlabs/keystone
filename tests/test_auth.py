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

import time
import uuid

import default_fixtures

from keystone import config
from keystone import exception
from keystone.openstack.common import timeutils
from keystone import test
from keystone import token
from keystone import trust


CONF = config.CONF


def _build_user_auth(token=None, username=None,
                     password=None, tenant_name=None,
                     trust_id=None):
    """Build auth dictionary.

    It will create an auth dictionary based on all the arguments
    that it receives.
    """
    auth_json = {}
    if token is not None:
        auth_json['token'] = token
    if username or password:
        auth_json['passwordCredentials'] = {}
    if username is not None:
        auth_json['passwordCredentials']['username'] = username
    if password is not None:
        auth_json['passwordCredentials']['password'] = password
    if tenant_name is not None:
        auth_json['tenantName'] = tenant_name
    if trust_id is not None:
        auth_json['trust'] = trust_id
    return auth_json


class AuthTest(test.TestCase):
    def setUp(self):
        super(AuthTest, self).setUp()

        CONF.identity.driver = 'keystone.identity.backends.kvs.Identity'
        self.load_backends()
        self.load_fixtures(default_fixtures)

        self.controller = token.controllers.Auth()

    def assertEqualTokens(self, a, b):
        """Assert that two tokens are equal.

        Compare two tokens except for their ids. This also truncates
        the time in the comparison.
        """
        def normalize(token):
            token['access']['token']['id'] = 'dummy'
            del token['access']['token']['expires']
            del token['access']['token']['issued_at']
            return token

        self.assertCloseEnoughForGovernmentWork(
            timeutils.parse_isotime(a['access']['token']['expires']),
            timeutils.parse_isotime(b['access']['token']['expires']))
        self.assertCloseEnoughForGovernmentWork(
            timeutils.parse_isotime(a['access']['token']['issued_at']),
            timeutils.parse_isotime(b['access']['token']['issued_at']))
        return self.assertDictEqual(normalize(a), normalize(b))


class AuthBadRequests(AuthTest):
    def setUp(self):
        super(AuthBadRequests, self).setUp()

    def test_no_external_auth(self):
        """Verify that _authenticate_external() raises exception if
        not applicable"""
        self.assertRaises(
            token.controllers.ExternalAuthNotApplicable,
            self.controller._authenticate_external,
            {}, {})

    def test_no_token_in_auth(self):
        """Verity that _authenticate_token() raises exception if no token"""
        self.assertRaises(
            exception.ValidationError,
            self.controller._authenticate_token,
            None, {})

    def test_no_credentials_in_auth(self):
        """Verity that _authenticate_local() raises exception if no creds"""
        self.assertRaises(
            exception.ValidationError,
            self.controller._authenticate_local,
            None, {})

    def test_authenticate_blank_request_body(self):
        """Verify sending empty json dict raises the right exception."""
        self.assertRaises(exception.ValidationError,
                          self.controller.authenticate,
                          {}, {})

    def test_authenticate_blank_auth(self):
        """Verify sending blank 'auth' raises the right exception."""
        body_dict = _build_user_auth()
        self.assertRaises(exception.ValidationError,
                          self.controller.authenticate,
                          {}, body_dict)

    def test_authenticate_invalid_auth_content(self):
        """Verify sending invalid 'auth' raises the right exception."""
        self.assertRaises(exception.ValidationError,
                          self.controller.authenticate,
                          {}, {'auth': 'abcd'})


class AuthWithToken(AuthTest):
    def setUp(self):
        super(AuthWithToken, self).setUp()

    def test_unscoped_token(self):
        """Verify getting an unscoped token with password creds"""
        body_dict = _build_user_auth(username='FOO',
                                     password='foo2')
        unscoped_token = self.controller.authenticate({}, body_dict)
        tenant = unscoped_token["access"]["token"].get("tenant", None)
        self.assertEqual(tenant, None)

    def test_auth_invalid_token(self):
        """Verify exception is raised if invalid token"""
        body_dict = _build_user_auth(token={"id": uuid.uuid4().hex})
        self.assertRaises(
            exception.Unauthorized,
            self.controller.authenticate,
            {}, body_dict)

    def test_auth_bad_formatted_token(self):
        """Verify exception is raised if invalid token"""
        body_dict = _build_user_auth(token={})
        self.assertRaises(
            exception.ValidationError,
            self.controller.authenticate,
            {}, body_dict)

    def test_auth_unscoped_token_no_tenant(self):
        """Verify getting an unscoped token with an unscoped token"""
        body_dict = _build_user_auth(
            username='FOO',
            password='foo2')
        unscoped_token = self.controller.authenticate({}, body_dict)

        body_dict = _build_user_auth(
            token=unscoped_token["access"]["token"])
        unscoped_token_2 = self.controller.authenticate({}, body_dict)

        self.assertEqualTokens(unscoped_token, unscoped_token_2)

    def test_auth_unscoped_token_tenant(self):
        """Verify getting a token in a tenant with an unscoped token"""
        # Add a role in so we can check we get this back
        self.identity_api.add_role_to_user_and_tenant(
            self.user_foo['id'],
            self.tenant_bar['id'],
            self.role_member['id'])
        # Get an unscoped tenant
        body_dict = _build_user_auth(
            username='FOO',
            password='foo2')
        unscoped_token = self.controller.authenticate({}, body_dict)
        # Get a token on BAR tenant using the unscoped tenant
        body_dict = _build_user_auth(
            token=unscoped_token["access"]["token"],
            tenant_name="BAR")
        scoped_token = self.controller.authenticate({}, body_dict)

        tenant = scoped_token["access"]["token"]["tenant"]
        roles = scoped_token["access"]["metadata"]["roles"]
        self.assertEquals(tenant["id"], self.tenant_bar['id'])
        self.assertEquals(roles[0], self.role_member['id'])

    def test_auth_token_tenant_group_role(self):
        """Verify getting a token in a tenant with group roles"""
        # Add a v2 style role in so we can check we get this back
        self.identity_api.add_role_to_user_and_tenant(
            self.user_foo['id'],
            self.tenant_bar['id'],
            self.role_member['id'])
        # Now create a group role for this user as well
        new_group = {'id': uuid.uuid4().hex, 'domain_id': uuid.uuid4().hex,
                     'name': uuid.uuid4().hex}
        self.identity_api.create_group(new_group['id'], new_group)
        self.identity_api.add_user_to_group(self.user_foo['id'],
                                            new_group['id'])
        self.identity_api.create_grant(
            group_id=new_group['id'],
            project_id=self.tenant_bar['id'],
            role_id=self.role_keystone_admin['id'])

        # Get a scoped token for the tenant
        body_dict = _build_user_auth(
            username='FOO',
            password='foo2',
            tenant_name="BAR")

        scoped_token = self.controller.authenticate({}, body_dict)

        tenant = scoped_token["access"]["token"]["tenant"]
        roles = scoped_token["access"]["metadata"]["roles"]
        self.assertEquals(tenant["id"], self.tenant_bar['id'])
        self.assertIn(self.role_member['id'], roles)
        self.assertIn(self.role_keystone_admin['id'], roles)


class AuthWithPasswordCredentials(AuthTest):
    def setUp(self):
        super(AuthWithPasswordCredentials, self).setUp()

    def test_auth_invalid_user(self):
        """Verify exception is raised if invalid user"""
        body_dict = _build_user_auth(
            username=uuid.uuid4().hex,
            password=uuid.uuid4().hex)
        self.assertRaises(
            exception.Unauthorized,
            self.controller.authenticate,
            {}, body_dict)

    def test_auth_valid_user_invalid_password(self):
        """Verify exception is raised if invalid password"""
        body_dict = _build_user_auth(
            username="FOO",
            password=uuid.uuid4().hex)
        self.assertRaises(
            exception.Unauthorized,
            self.controller.authenticate,
            {}, body_dict)

    def test_auth_empty_password(self):
        """Verify exception is raised if empty password"""
        body_dict = _build_user_auth(
            username="FOO",
            password="")
        self.assertRaises(
            exception.Unauthorized,
            self.controller.authenticate,
            {}, body_dict)

    def test_auth_no_password(self):
        """Verify exception is raised if empty password"""
        body_dict = _build_user_auth(username="FOO")
        self.assertRaises(
            exception.ValidationError,
            self.controller.authenticate,
            {}, body_dict)

    def test_authenticate_blank_password_credentials(self):
        """Verify sending empty json dict as passwordCredentials raises the
        right exception."""
        body_dict = {'passwordCredentials': {}, 'tenantName': 'demo'}
        self.assertRaises(exception.ValidationError,
                          self.controller.authenticate,
                          {}, body_dict)

    def test_authenticate_no_username(self):
        """Verify skipping username raises the right exception."""
        body_dict = _build_user_auth(password="pass",
                                     tenant_name="demo")
        self.assertRaises(exception.ValidationError,
                          self.controller.authenticate,
                          {}, body_dict)


class AuthWithRemoteUser(AuthTest):
    def setUp(self):
        super(AuthWithRemoteUser, self).setUp()

    def test_unscoped_remote_authn(self):
        """Verify getting an unscoped token with external authn"""
        body_dict = _build_user_auth(
            username='FOO',
            password='foo2')
        local_token = self.controller.authenticate(
            {}, body_dict)

        body_dict = _build_user_auth()
        remote_token = self.controller.authenticate(
            {'REMOTE_USER': 'FOO'}, body_dict)

        self.assertEqualTokens(local_token, remote_token)

    def test_unscoped_remote_authn_jsonless(self):
        """Verify that external auth with invalid request fails"""
        self.assertRaises(
            exception.ValidationError,
            self.controller.authenticate,
            {'REMOTE_USER': 'FOO'},
            None)

    def test_scoped_remote_authn(self):
        """Verify getting a token with external authn"""
        body_dict = _build_user_auth(
            username='FOO',
            password='foo2',
            tenant_name='BAR')
        local_token = self.controller.authenticate(
            {}, body_dict)

        body_dict = _build_user_auth(
            tenant_name='BAR')
        remote_token = self.controller.authenticate(
            {'REMOTE_USER': 'FOO'}, body_dict)

        self.assertEqualTokens(local_token, remote_token)

    def test_scoped_nometa_remote_authn(self):
        """Verify getting a token with external authn and no metadata"""
        body_dict = _build_user_auth(
            username='TWO',
            password='two2',
            tenant_name='BAZ')
        local_token = self.controller.authenticate(
            {}, body_dict)

        body_dict = _build_user_auth(tenant_name='BAZ')
        remote_token = self.controller.authenticate(
            {'REMOTE_USER': 'TWO'}, body_dict)

        self.assertEqualTokens(local_token, remote_token)

    def test_scoped_remote_authn_invalid_user(self):
        """Verify that external auth with invalid user fails"""
        body_dict = _build_user_auth(tenant_name="BAR")
        self.assertRaises(
            exception.Unauthorized,
            self.controller.authenticate,
            {'REMOTE_USER': uuid.uuid4().hex},
            body_dict)


class AuthWithTrust(AuthTest):
    def setUp(self):
        super(AuthWithTrust, self).setUp()

        trust.Manager()
        self.trust_api = trust.controllers.Trust()
        self.sample_data = {'trustor': self.user_foo['id'],
                            'trustee': self.user_two['id'],
                            'tenant': self.tenant_bar['id'],
                            'roles': [self.role_browser['id']],
                            'endpoints': ["e1", "e2", "e3"]}
        self.create_trust()

    def create_trust(self):
        username = self.user_foo['name'],
        password = 'foo2'
        body_dict = _build_user_auth(username=username, password=password)
        self.unscoped_token = self.controller.authenticate({}, body_dict)
        context = {'token_id': self.unscoped_token['access']['token']['id']}
        new_trust = self.trust_api.create(context, self.sample_data)
        self.new_trust = new_trust['trust']

    def build_request_body(self, username, password):
        body_dict = _build_user_auth(username=username, password=password)
        self.unscoped_token = self.controller.authenticate({}, body_dict)
        unscoped_token_id = self.unscoped_token['access']['token']['id']
        request_body = _build_user_auth(token={'id': unscoped_token_id},
                                        trust_id=self.new_trust['id'])
        return request_body

    def test_create_trust(self):
        self.assertEquals(self.new_trust['trustor'], self.user_foo['id'])
        self.assertEquals(self.new_trust['trustee'], self.user_two['id'])
        self.assertEquals(self.new_trust['roles'], [self.role_browser['id']])
        #TODO Endpoints

    def test_token_from_trust_wrong_user_fails(self):
        new_trust = self.create_trust()
        request_body = self.build_request_body('FOO', 'foo2')
        self.assertRaises(
            exception.Unauthorized,
            self.controller.authenticate, {}, request_body)

    def test_token_from_trust(self):
        self.identity_api.add_role_to_user_and_tenant(self.user_foo['id'],
                                                      self.tenant_bar['id'],
                                                      self.role_member['id'])

        self.identity_api.add_role_to_user_and_tenant(self.user_foo['id'],
                                                      self.tenant_bar['id'],
                                                      self.role_browser['id'])

        request_body = self.build_request_body('TWO', 'two2')
        auth_response = self.controller.authenticate({}, request_body)

        self.assertIsNotNone(auth_response)
        self.assertEquals(['browser'],
                          auth_response['access']['metadata']['roles'],
                          "user_foo has two roles, but the token should only"
                          " get the role specified in the trust.")

    def test_token_from_trust_with_no_role_fails(self):
        request_body = self.build_request_body('TWO', 'two2')
        self.assertRaises(
            exception.Unauthorized,
            self.controller.authenticate, {}, request_body)

    def test_token_from_trust_with_wrong_role_fails(self):
        self.identity_api.add_role_to_user_and_tenant(self.user_foo['id'],
                                                      self.tenant_bar['id'],
                                                      self.role_member['id'])
        request_body = self.build_request_body('TWO', 'two2')

        self.assertRaises(
            exception.Unauthorized,
            self.controller.authenticate, {}, request_body)


class TokenExpirationTest(AuthTest):
    def _maintain_token_expiration(self):
        """Token expiration should be maintained after re-auth & validation."""
        r = self.controller.authenticate(
            {},
            auth={
                'passwordCredentials': {
                    'username': self.user_foo['name'],
                    'password': self.user_foo['password']
                }
            })
        unscoped_token_id = r['access']['token']['id']
        original_expiration = r['access']['token']['expires']

        time.sleep(0.5)

        r = self.controller.validate_token(
            dict(is_admin=True, query_string={}),
            token_id=unscoped_token_id)
        self.assertEqual(original_expiration, r['access']['token']['expires'])

        time.sleep(0.5)

        r = self.controller.authenticate(
            {},
            auth={
                'token': {
                    'id': unscoped_token_id,
                },
                'tenantId': self.tenant_bar['id'],
            })
        scoped_token_id = r['access']['token']['id']
        self.assertEqual(original_expiration, r['access']['token']['expires'])

        time.sleep(0.5)

        r = self.controller.validate_token(
            dict(is_admin=True, query_string={}),
            token_id=scoped_token_id)
        self.assertEqual(original_expiration, r['access']['token']['expires'])

    def test_maintain_uuid_token_expiration(self):
        self.opt_in_group('signing', token_format='UUID')
        self._maintain_token_expiration()
