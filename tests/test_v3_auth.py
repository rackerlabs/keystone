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

from keystone import auth
from keystone import config
from keystone import exception
from keystone.openstack.common import timeutils
from keystone import test

import default_fixtures
import test_v3


CONF = config.CONF


def _build_auth_scope(project_id=None, project_name=None,
                      project_domain_id=None, project_domain_name=None,
                      domain_id=None, domain_name=None):
    scope_data = {}
    if project_id or project_name:
        scope_data['project'] = {}
        if project_id:
            scope_data['project']['id'] = project_id
        else:
            scope_data['project']['name'] = project_name
            if project_domain_id or project_domain_name:
                project_domain_json = {}
                if project_domain_id:
                    project_domain_json['id'] = project_domain_id
                else:
                    project_domain_json['name'] = project_domain_name
                scope_data['project']['domain'] = project_domain_json
    if domain_id or domain_name:
        scope_data['domain'] = {}
        if domain_id:
            scope_data['domain']['id'] = domain_id
        else:
            scope_data['domain']['name'] = domain_name
    return scope_data


def _build_password_auth(user_id=None, username=None,
                         user_domain_id=None, user_domain_name=None,
                         password=None):
    password_data = {'user': {}}
    if user_id:
        password_data['user']['id'] = user_id
    else:
        password_data['user']['name'] = username
        if user_domain_id or user_domain_name:
            password_data['user']['domain'] = {}
            if user_domain_id:
                password_data['user']['domain']['id'] = user_domain_id
            else:
                password_data['user']['domain']['name'] = user_domain_name
    password_data['user']['password'] = password
    return password_data


def _build_token_auth(token):
    return {'id': token}


def _build_authentication_request(token=None, user_id=None, username=None,
                                  user_domain_id=None, user_domain_name=None,
                                  password=None, project_id=None,
                                  project_name=None, project_domain_id=None,
                                  project_domain_name=None,
                                  domain_id=None, domain_name=None):
    """Build auth dictionary.

    It will create an auth dictionary based on all the arguments
    that it receives.
    """
    auth_data = {}
    auth_data['authentication'] = {'methods': []}
    if token:
        auth_data['authentication']['methods'].append('token')
        auth_data['authentication']['token'] = _build_token_auth(token)
    if user_id or username:
        auth_data['authentication']['methods'].append('password')
        auth_data['authentication']['password'] = _build_password_auth(
            user_id, username, user_domain_id, user_domain_name, password)
    if project_id or project_name or domain_id or domain_name:
        auth_data['scope'] = _build_auth_scope(project_id,
                                               project_name,
                                               project_domain_id,
                                               project_domain_name,
                                               domain_id,
                                               domain_name)
    return auth_data


class AuthTest(test_v3.RestfulTestCase):
    def setUp(self):
        super(AuthTest, self).setUp()
        self.load_fixtures(default_fixtures)
        self.identity_api.add_role_to_user_and_project(
            self.user_foo['id'], self.tenant_bar['id'],
            self.role_keystone_admin['id'])

        self.domain_id = uuid.uuid4().hex
        self.domain = self.new_domain_ref()
        self.domain['id'] = self.domain_id
        domain_ref = self.identity_api.create_domain(self.domain_id,
                                                     self.domain)
        self.domain_name = domain_ref['name']

        self.project_id = uuid.uuid4().hex
        self.project = self.new_project_ref(
            domain_id=self.domain_id)
        self.project['id'] = self.project_id
        project_ref = self.identity_api.create_project(self.project_id,
                                                       self.project)
        self.project_name = project_ref['name']

        self.user_id = uuid.uuid4().hex
        self.password = uuid.uuid4().hex
        self.user = self.new_user_ref(
            domain_id=self.domain_id)
        self.user['password'] = self.password
        self.user['id'] = self.user_id
        user_ref = self.identity_api.create_user(self.user_id, self.user)
        self.user_name = user_ref['name']

        self.role_id = uuid.uuid4().hex
        self.role = self.new_role_ref()
        self.role['id'] = self.role_id
        self.identity_api.create_role(self.role_id, self.role)
        self.identity_api.add_role_to_user_and_project(self.user_id,
                                                       self.project_id,
                                                       self.role_id)

    def tearDown(self):
        super(AuthTest, self).tearDown()
        # need to reset the plug-ins
        auth.controllers.AUTH_METHODS = {}

    def assertUnscopedToken(self, token):
        self.assertEqual([], token['roles'])
        self.assertEqual(self.user_id, token['user']['id'])

    def assertScopedToken(self, token):
        self.assertNotEqual([], token['roles'])
        self.assertEqual(self.user_id, token['user']['id'])
        self.assertEqual(self.role_id, token['roles'][0]['id'])

    def assertValidErrorResponse(self, r):
        pass

    def assertEqualTokens(self, a, b):
        """Assert that two tokens are equal.

        Compare two tokens except for their ids. This also truncates
        the time in the comparison.
        """
        def normalize(token):
            del token['expires']
            del token['issued_at']
            return token

        self.assertCloseEnoughForGovernmentWork(
            timeutils.parse_isotime(a['expires']),
            timeutils.parse_isotime(b['expires']))
        self.assertCloseEnoughForGovernmentWork(
            timeutils.parse_isotime(a['issued_at']),
            timeutils.parse_isotime(b['issued_at']))
        return self.assertDictEqual(normalize(a), normalize(b))


class TestAuthInfo(test.TestCase):
    def setUp(self):
        super(TestAuthInfo, self).setUp()

    def test_missing_auth_methods(self):
        auth_data = {'authentication': {}}
        auth_data['authentication']['token'] = {'id': uuid.uuid4().hex}
        self.assertRaises(exception.ValidationError,
                          auth.controllers.AuthInfo,
                          None,
                          auth_data)

    def test_unsupported_auth_method(self):
        auth_data = {'methods': ['abc']}
        auth_data['abc'] = {'test': 'test'}
        auth_data = {'authentication': auth_data}
        self.assertRaises(exception.AuthMethodNotSupported,
                          auth.controllers.AuthInfo,
                          None,
                          auth_data)

    def test_missing_auth_method_data(self):
        auth_data = {'methods': ['password']}
        auth_data = {'authentication': auth_data}
        self.assertRaises(exception.ValidationError,
                          auth.controllers.AuthInfo,
                          None,
                          auth_data)

    def test_project_name_no_domain(self):
        auth_data = _build_authentication_request(username='test',
                                                  password='test',
                                                  project_name='abc')
        self.assertRaises(exception.ValidationError,
                          auth.controllers.AuthInfo,
                          None,
                          auth_data)

    def test_both_project_and_domain_in_scope(self):
        auth_data = _build_authentication_request(user_id='test',
                                                  password='test',
                                                  project_name='test',
                                                  domain_name='test')
        self.assertRaises(exception.ValidationError,
                          auth.controllers.AuthInfo,
                          None,
                          auth_data)


class TestTokenAPIs(AuthTest):
    def setUp(self):
        super(TestTokenAPIs, self).setUp()
        auth_data = _build_authentication_request(
            username=self.user_name,
            user_domain_id=self.domain_id,
            password=self.password)
        resp = self.post('/auth/tokens', body=auth_data)
        self.token_data = resp.body
        self.token = resp.getheader('X-Subject-Token')
        self.headers = {'X-Subject-Token': resp.getheader('X-Subject-Token')}

    def test_default_fixture_scope_token(self):
        self.assertIsNotNone(self.get_scoped_token())

    def test_rescoping_token(self):
        expires = self.token_data['expires']
        auth_data = _build_authentication_request(
            token=self.token,
            project_id=self.project_id)
        resp = self.post('/auth/tokens', body=auth_data)
        self.assertScopedToken(resp.body)
        # make sure expires stayed the same
        self.assertEqual(expires, resp.body['expires'])

    def test_check_token(self):
        resp = self.head('/auth/tokens', headers=self.headers)
        self.assertEqual(resp.status, 204)

    def test_validate_token(self):
        resp = self.get('/auth/tokens', headers=self.headers)
        self.assertUnscopedToken(resp.body)

    def test_revoke_token(self):
        self.delete('/auth/tokens', headers=self.headers)

        # make sure token no longer valid
        resp = self.head('/auth/tokens', headers=self.headers, expected_status=401)
        self.assertEqual(resp.status, 401)

        # make sure we have a CRL
        resp = self.get('/auth/tokens/revoked')
        self.assertTrue('signed' in resp.body)


class TestAuth(AuthTest):
    def test_unscope_token_with_name(self):
        auth_data = _build_authentication_request(
            username=self.user_name,
            user_domain_id=self.domain_id,
            password=self.password)
        resp = self.post('/auth/tokens', body=auth_data)
        self.assertUnscopedToken(resp.body)

    def test_project_scope_token_with_name(self):
        auth_data = _build_authentication_request(
            username=self.user_name,
            user_domain_id=self.domain_id,
            password=self.password,
            project_id=self.project_id)
        resp = self.post('/auth/tokens', body=auth_data)
        self.assertScopedToken(resp.body)

    def test_auth_with_id(self):
        auth_data = _build_authentication_request(
            user_id=self.user_id,
            password=self.password)
        resp = self.post('/auth/tokens', body=auth_data)
        self.assertUnscopedToken(resp.body)

        token = resp.getheader('X-Subject-Token')
        headers = {'X-Subject-Token': resp.getheader('X-Subject-Token')}

        # test token auth
        auth_data = _build_authentication_request(token=token)
        resp = self.post('/auth/tokens', body=auth_data)
        self.assertUnscopedToken(resp.body)

    def test_remote_user(self):
        auth_data = _build_authentication_request(
            user_id=self.user_id,
            password=self.password)
        api = auth.controllers.Auth()
        context = {'REMOTE_USER': self.user_name}
        auth_info = auth.controllers.AuthInfo(None, auth_data)
        auth_context = {'extras': {}, 'method_names': []}
        api.authenticate(context, auth_info, auth_context)
        self.assertEqual(auth_context['user_id'], self.user_id)

    def test_remote_user_no_domain(self):
        auth_data = _build_authentication_request(
            username=self.user_name,
            password=self.password)
        api = auth.controllers.Auth()
        context = {'REMOTE_USER': self.user_name}
        auth_info = auth.controllers.AuthInfo(None, auth_data)
        auth_context = {'extras': {}, 'method_names': []}
        self.assertRaises(exception.ValidationError,
                          api.authenticate,
                          context,
                          auth_info,
                          auth_context)
