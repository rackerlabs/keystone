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

from oslo_config import cfg
import webob
import uuid

from keystone.auth import controllers
from keystone.common import authorization
from keystone import middleware
from keystone.tests import unit as tests
from keystone.tests.unit import test_backend_sql


CONF = cfg.CONF


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

    def test_not_dict_body(self):
        req = make_request(body='42',
                           content_type='application/json',
                           method='POST')
        resp = middleware.JsonBodyMiddleware(None).process_request(req)
        self.assertEqual(400, resp.status_int)
        self.assertTrue('valid JSON object' in resp.json['error']['message'])

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

class AuthContextMiddlewareTest(test_backend_sql.SqlTests, tests.TestCase):

    def setUp(self):
        super(AuthContextMiddlewareTest, self).setUp()

        self.client_issuer = 'emailAddress=userA@domainA.com,CN=userA,' \
                             'OU=projectA,O=domainA.com,L=Sunnyvale,' \
                             'ST=California,C=US'
        self.untrusted_client_issuer = 'CN=foo,O=fooCafe,L=San Francisco,' \
                                       'ST=California,C=US'
        self.trusted_issuer = 'emailAddress%3DuserA%40domainA.com%2C' \
                              'CN%3DuserA%2COU%3DprojectA%2C' \
                              'O%3DdomainA.com%2CL%3DSunnyvale%2C' \
                              'ST%3DCalifornia%2CC%3DUS'
        CONF.tokenless_auth.trusted_issuers = [self.trusted_issuer]
        CONF.tokenless_auth.methods = ['external','password','token']
        controllers.load_auth_methods()
        self.load_sample_data()

    def load_sample_data(self):
        self.domain_id = uuid.uuid4().hex
        self.domain_name = 'domainA.com'
        self.project_id = uuid.uuid4().hex
        self.project_name = 'projectA'
        self.user_name = 'userA'
        self.user_password = uuid.uuid4().hex
        self.user_email = 'userA@domainA.com'
        # This idp_is is calculated based on
        # base64(sha256(self.client_issuer))
        self.idp_id = 'ft/ZbwtftULvL+gb2yO1d9X23WZ4kZ0yRvOufM6RCmo='
        self.protocol_id = CONF.tokenless_auth.protocol
        self.role_id = uuid.uuid4().hex
        self.role_name = 'roleA'

        # 1) Create a domain for the user.
        self.domain = {
            'description': uuid.uuid4().hex,
            'enabled': True,
            'id': self.domain_id,
            'name': self.domain_name,
        }

        self.resource_api.create_domain(self.domain_id, self.domain)

        # 2) Create a project for the user.
        self.project = {
            'description': uuid.uuid4().hex,
            "domain_id": self.domain_id,
            'enabled': True,
            'id': self.project_id,
            'name': self.project_name,
        }

        self.resource_api.create_project(self.project_id, self.project)

        # 3) Create an user in new domain.
        self.user = {
            'name': self.user_name,
            'domain_id': self.domain_id,
            'project_id': self.project_id,
            'password': self.user_password,
            'email': self.user_email,
        }

        self.user = self.identity_api.create_user(self.user)

        self.rules = {
            'rules': [
                {
                    'local': [
                        {
                            'user': {
                                'name': '{0}',
                                'domain_name': '{1}'
                            }
                        }
                    ],
                    'remote': [
                        {
                            'type': 'SSL_CLIENT_S_DN_CN'
                        },
                        {
                            'type': 'SSL_CLIENT_I_DN_O'
                        }
                    ]
                }
            ]
        }

        # Add IDP
        self.idp = self.idp_ref(id=self.idp_id)
        self.federation_api.create_idp(self.idp['id'],
                                       self.idp)

        # Add a mapping
        self.mapping = self.mapping_ref(rules=self.rules)
        self.federation_api.create_mapping(self.mapping['id'],
                                           self.mapping)
        # Add protocols
        self.proto_x509 = self.proto_ref(mapping_id=self.mapping['id'])
        self.proto_x509['id'] = self.protocol_id
        self.federation_api.create_protocol(self.idp['id'],
                                            self.proto_x509['id'],
                                            self.proto_x509)

        # Add a role
        self.role = {
            'id': self.role_id,
            'name': self.role_name,
        }
        self.role_api.create_role(self.role_id, self.role)

        # Assign a role to the user on a project
        self.assignment_api.add_role_to_user_and_project(
                user_id=self.user['id'],
                tenant_id=self.project_id,
                role_id=self.role_id)

    def idp_ref(self, id=None):
        idp = {
            'id': id or uuid.uuid4().hex,
            'enabled': True,
            'description': uuid.uuid4().hex
        }
        return idp

    def proto_ref(self, mapping_id=None):
        proto = {
            'id': uuid.uuid4().hex,
            'mapping_id': mapping_id or uuid.uuid4().hex
        }
        return proto

    def mapping_ref(self, rules=None):
        return {
            'id': uuid.uuid4().hex,
            'rules': self.rules['rules']
        }

    def test_context_already_exists(self):
        req = make_request()
        token_id = uuid.uuid4().hex
        req.environ[authorization.AUTH_CONTEXT_ENV] = {'token_id': token_id}
        middleware.AuthContextMiddleware(None).process_request(req)
        context = req.environ[authorization.AUTH_CONTEXT_ENV]
        self.assertEqual(token_id, context['token_id'])

    def test_not_applicable_to_token_request(self):
        req = make_request()
        req.environ['PATH_INFO'] = '/auth/tokens'
        req.environ['REQUEST_METHOD'] = 'POST'
        middleware.AuthContextMiddleware(None).process_request(req)
        context = req.environ.get(authorization.AUTH_CONTEXT_ENV)
        self.assertEqual(None, context)

    def test_no_tokenless_attributes_request(self):
        req = make_request()
        middleware.AuthContextMiddleware(None).process_request(req)
        context = req.environ.get(authorization.AUTH_CONTEXT_ENV)
        self.assertEqual(None, context)

    def test_no_issuer_attribute_request(self):
        req = make_request()
        req.environ['HTTP_X_PROJECT_ID'] = uuid.uuid4().hex
        middleware.AuthContextMiddleware(None).process_request(req)
        context = req.environ.get(authorization.AUTH_CONTEXT_ENV)
        self.assertEqual(None, context)

    def test_has_only_issuer_and_project_name_request(self):
        req = make_request()
        req.environ[CONF.tokenless_auth.issuer_attribute] = uuid.uuid4().hex
        req.environ['HTTP_X_PROJECT_NAME'] = uuid.uuid4().hex
        middleware.AuthContextMiddleware(None).process_request(req)
        context = req.environ.get(authorization.AUTH_CONTEXT_ENV)
        self.assertEqual(None, context)

    def test_has_only_issuer_and_project_domain_name_request(self):
        req = make_request()
        req.environ[CONF.tokenless_auth.issuer_attribute] = uuid.uuid4().hex
        req.environ['HTTP_X_PROJECT_DOMAIN_NAME'] = uuid.uuid4().hex
        middleware.AuthContextMiddleware(None).process_request(req)
        context = req.environ.get(authorization.AUTH_CONTEXT_ENV)
        self.assertEqual(None, context)

    def test_has_only_issuer_and_project_domain_id_request(self):
        req = make_request()
        req.environ[CONF.tokenless_auth.issuer_attribute] = uuid.uuid4().hex
        req.environ['HTTP_X_PROJECT_DOMAIN_ID'] = uuid.uuid4().hex
        middleware.AuthContextMiddleware(None).process_request(req)
        context = req.environ.get(authorization.AUTH_CONTEXT_ENV)
        self.assertEqual(None, context)

    def test_empty_trusted_issuer_list(self):
        req = make_request()
        req.environ[CONF.tokenless_auth.issuer_attribute] = uuid.uuid4().hex
        req.environ['HTTP_X_PROJECT_ID'] = uuid.uuid4().hex
        CONF.tokenless_auth.trusted_issuers = []
        middleware.AuthContextMiddleware(None).process_request(req)
        context = req.environ.get(authorization.AUTH_CONTEXT_ENV)
        self.assertEqual(None, context)

    def test_client_issuer_not_trusted(self):
        req = make_request()
        req.environ[CONF.tokenless_auth.issuer_attribute] = \
            self.untrusted_client_issuer
        req.environ['HTTP_X_PROJECT_ID'] = uuid.uuid4().hex
        middleware.AuthContextMiddleware(None).process_request(req)
        context = req.environ.get(authorization.AUTH_CONTEXT_ENV)
        self.assertEqual(None, context)

    def test_proj_scope_with_proj_id_and_proj_dom_id_success(self):
        req = make_request()
        req.environ[CONF.tokenless_auth.issuer_attribute] = self.client_issuer
        req.environ['HTTP_X_PROJECT_ID'] = self.project_id
        req.environ['HTTP_X_PROJECT_DOMAIN_ID'] = self.domain_id
        req.environ['SSL_CLIENT_S_DN_CN'] = self.user_name
        req.environ['SSL_CLIENT_I_DN_O'] = self.domain_name
        middleware.AuthContextMiddleware(None).process_request(req)
        context = req.environ.get(authorization.AUTH_CONTEXT_ENV)
        self.assertIsNotNone(context)
        self.assertEqual(context['project_id'], self.project['id'])
        self.assertEqual(context['user_id'], self.user['id'])
        self.assertEqual(context['roles'][0], self.role_name)

    def test_proj_scope_with_proj_id_only_success(self):
        req = make_request()
        req.environ[CONF.tokenless_auth.issuer_attribute] = self.client_issuer
        req.environ['HTTP_X_PROJECT_ID'] = self.project_id
        req.environ['SSL_CLIENT_S_DN_CN'] = self.user_name
        req.environ['SSL_CLIENT_I_DN_O'] = self.domain_name
        middleware.AuthContextMiddleware(None).process_request(req)
        context = req.environ.get(authorization.AUTH_CONTEXT_ENV)
        self.assertIsNotNone(context)
        self.assertEqual(context['project_id'], self.project['id'])
        self.assertEqual(context['user_id'], self.user['id'])
        self.assertEqual(context['roles'][0], self.role_name)

    def test_proj_scope_with_proj_name_and_proj_dom_id_success(self):
        req = make_request()
        req.environ[CONF.tokenless_auth.issuer_attribute] = self.client_issuer
        req.environ['HTTP_X_PROJECT_NAME'] = self.project_name
        req.environ['HTTP_X_PROJECT_DOMAIN_ID'] = self.domain_id
        req.environ['SSL_CLIENT_S_DN_CN'] = self.user_name
        req.environ['SSL_CLIENT_I_DN_O'] = self.domain_name
        middleware.AuthContextMiddleware(None).process_request(req)
        context = req.environ.get(authorization.AUTH_CONTEXT_ENV)
        self.assertIsNotNone(context)
        self.assertEqual(context['project_id'], self.project['id'])
        self.assertEqual(context['user_id'], self.user['id'])
        self.assertEqual(context['roles'][0], self.role_name)

    def test_proj_scope_with_proj_name_and_proj_dom_name_success(self):
        req = make_request()
        req.environ[CONF.tokenless_auth.issuer_attribute] = self.client_issuer
        req.environ['HTTP_X_PROJECT_NAME'] = self.project_name
        req.environ['HTTP_X_PROJECT_DOMAIN_NAME'] = self.domain_name
        req.environ['SSL_CLIENT_S_DN_CN'] = self.user_name
        req.environ['SSL_CLIENT_I_DN_O'] = self.domain_name
        middleware.AuthContextMiddleware(None).process_request(req)
        context = req.environ.get(authorization.AUTH_CONTEXT_ENV)
        self.assertIsNotNone(context)
        self.assertEqual(context['project_id'], self.project['id'])
        self.assertEqual(context['user_id'], self.user['id'])
        self.assertEqual(context['roles'][0], self.role_name)

    def test_proj_scope_with_proj_name_only_fail(self):
        req = make_request()
        req.environ[CONF.tokenless_auth.issuer_attribute] = self.client_issuer
        req.environ['HTTP_X_PROJECT_NAME'] = self.project_id
        req.environ['SSL_CLIENT_S_DN_CN'] = self.user_name
        req.environ['SSL_CLIENT_I_DN_O'] = self.domain_name
        middleware.AuthContextMiddleware(None).process_request(req)
        context = req.environ.get(authorization.AUTH_CONTEXT_ENV)
        self.assertEqual(None, context)
