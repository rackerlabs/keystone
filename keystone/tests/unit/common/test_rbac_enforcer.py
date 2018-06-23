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

import uuid

import flask
from flask import blueprints
from flask import g
import flask_restful

from keystone.common import authorization
from keystone.common import context
from keystone.common import provider_api
from keystone.common import rbac_enforcer
from keystone import exception
from keystone.models import token_model
from keystone.tests import unit
from keystone.tests.unit import rest


PROVIDER_APIS = provider_api.ProviderAPIs


class TestRBACEnforcer(unit.TestCase):

    def test_enforcer_shared_state(self):
        enforcer = rbac_enforcer.enforcer.RBACEnforcer()
        enforcer2 = rbac_enforcer.enforcer.RBACEnforcer()

        self.assertIsNotNone(enforcer._enforcer)
        self.assertEqual(enforcer._enforcer, enforcer2._enforcer)
        setattr(enforcer, '_test_attr', uuid.uuid4().hex)
        self.assertEqual(enforcer._test_attr, enforcer2._test_attr)

    def test_enforcer_auto_instantiated(self):
        enforcer = rbac_enforcer.enforcer.RBACEnforcer()
        # Check that the enforcer instantiates the oslo_policy enforcer object
        # on demand.
        self.assertIsNotNone(enforcer._enforcer)
        enforcer._reset()
        self.assertIsNotNone(enforcer._enforcer)


class _TestRBACEnforcerBase(rest.RestfulTestCase):

    def setUp(self):
        super(_TestRBACEnforcerBase, self).setUp()
        self._setup_dynmic_flask_blueprint_api()
        self._setup_flask_restful_api()

    def _setup_dynmic_flask_blueprint_api(self):
        # Create a dynamic flask blueprint with a known prefix
        api = uuid.uuid4().hex
        url_prefix = '/_%s_TEST' % api
        blueprint = blueprints.Blueprint(api, __name__, url_prefix=url_prefix)
        self.url_prefix = url_prefix
        self.flask_blueprint = blueprint
        self.cleanup_instance('flask_blueprint', 'url_prefix')

    def _setup_flask_restful_api(self):
        self.restful_api_url_prefix = '/_%s_TEST' % uuid.uuid4().hex
        self.restful_api = flask_restful.Api(self.public_app.app,
                                             self.restful_api_url_prefix)

        # Very Basic Restful Resource
        class RestfulResource(flask_restful.Resource):
            def get(self, argument_id):
                return {'argument': {argument_id: {'value': 'TEST'}}}

        self.restful_api_resource = RestfulResource
        self.restful_api.add_resource(
            RestfulResource, '/argument/<string:argument_id>')
        self.cleanup_instance('restful_api', 'restful_resource',
                              'restful_api_url_prefix')

    def _register_blueprint_to_app(self):
        # TODO(morgan): remove the need for webtest, but for now just unwrap
        # by one layer. Once everything is converted to flask, we can fix
        # the tests to eliminate "webtest".
        self.public_app.app.register_blueprint(
            self.flask_blueprint, url_prefix=self.url_prefix)

    def _auth_json(self):
        return {
            'auth': {
                'identity': {
                    'methods': ['password'],
                    'password': {
                        'user': {
                            'name': self.user_req_admin['name'],
                            'password': self.user_req_admin['password'],
                            'domain': {
                                'id': self.user_req_admin['domain_id']
                            }
                        }
                    }
                },
                'scope': {
                    'project': {
                        'id': self.tenant_service['id']
                    }
                }
            }
        }


class TestRBACEnforcerRestAdminAuthToken(_TestRBACEnforcerBase):

    def config_overrides(self):
        super(TestRBACEnforcerRestAdminAuthToken, self).config_overrides()
        self.config_fixture.config(admin_token='ADMIN')

    def test_enforcer_is_admin_check_with_token(self):
        # Admin-shared token passed and valid, "is_admin" should be true.
        enforcer = rbac_enforcer.enforcer.RBACEnforcer()
        with self.test_client() as c:
            c.get('%s/argument/%s' % (self.restful_api_url_prefix,
                                      uuid.uuid4().hex),
                  headers={authorization.AUTH_TOKEN_HEADER: 'ADMIN'})
            self.assertTrue(enforcer._is_admin())

    def test_enforcer_is_admin_check_without_token(self):
        enforcer = rbac_enforcer.enforcer.RBACEnforcer()
        with self.test_client() as c:
            # Admin-shared token passed and invalid, "is_admin" should be false
            c.get('%s/argument/%s' % (self.restful_api_url_prefix,
                                      uuid.uuid4().hex),
                  headers={authorization.AUTH_TOKEN_HEADER: 'BOGUS'})
            self.assertFalse(enforcer._is_admin())

            # Admin-shared token not passed, "is_admin" should be false
            c.get('%s/argument/%s' % (self.restful_api_url_prefix,
                                      uuid.uuid4().hex))
            self.assertFalse(enforcer._is_admin())

    def test_enforce_call_is_admin(self):
        self.skipTest('Test Not Implemented')


class TestRBACEnforcerRest(_TestRBACEnforcerBase):

    def test_extract_subject_token_target_data(self):
        enforcer = rbac_enforcer.enforcer.RBACEnforcer()

        path = '/v3/auth/tokens'
        body = self._auth_json()

        with self.test_client() as c:
            r = c.post(
                path,
                json=body,
                follow_redirects=True,
                expected_status_code=201)

            token_id = r.headers['X-Subject-Token']

            c.get('/v3', headers={'X-Auth-Token': token_id,
                                  'X-Subject-Token': token_id})
            token_ref = token_model.KeystoneToken(
                token_id=token_id,
                token_data=PROVIDER_APIS.token_provider_api.validate_token(
                    token_id
                )
            )
            subj_token_data = enforcer._extract_subject_token_target_data()
            subj_token_data = subj_token_data['token']
            self.assertEqual(token_ref.user_id, subj_token_data['user_id'])
            self.assertIn('user', subj_token_data)
            self.assertIn('domain', subj_token_data['user'])
            self.assertEqual(token_ref.user_domain_id,
                             subj_token_data['user']['domain']['id'])

    def test_extract_filter_data(self):
        # Test that we are extracting useful filter data from the
        # request context. The tested function validates tha
        # extract_filter_attr only adds the passed filter values to the
        # policy dict, all other query-params are ignored.

        path = uuid.uuid4().hex

        @self.flask_blueprint.route('/%s' % path)
        def return_nothing_interesting():
            return 'OK', 200

        self._register_blueprint_to_app()

        with self.test_client() as c:
            expected_param = uuid.uuid4().hex
            unexpected_param = uuid.uuid4().hex
            get_path = '/'.join([self.url_prefix, path])
            # Populate the query-string with two params, one that should
            # exist and one that should not in the resulting policy
            # dict.
            qs = '%(expected)s=EXPECTED&%(unexpected)s=UNEXPECTED' % {
                'expected': expected_param,
                'unexpected': unexpected_param
            }
            # Perform the get with the query-string
            c.get('%(path)s?%(qs)s' % {'path': get_path, 'qs': qs})
            enforcer = rbac_enforcer.enforcer.RBACEnforcer()
            # Extract the filter values.
            extracted_filter = enforcer._extract_filter_values(
                [expected_param])
            # Unexpected param is not in the extracted values
            # Expected param is in the extracted values
            # Expected param has the expected value
            self.assertNotIn(extracted_filter, unexpected_param)
            self.assertIn(expected_param, expected_param)
            self.assertEqual(extracted_filter[expected_param], 'EXPECTED')

    def test_retrive_oslo_req_context(self):
        # Test to ensure 'get_oslo_req_context' is pulling the request context
        # from the environ as expected. The only way to really test is an
        # instance check.
        with self.test_client() as c:
            c.get('%s/argument/%s' % (self.restful_api_url_prefix,
                                      uuid.uuid4().hex))
            enforcer = rbac_enforcer.enforcer.RBACEnforcer()
            oslo_req_context = enforcer._get_oslo_req_context()
            self.assertIsInstance(oslo_req_context, context.RequestContext)

    def test_is_authenticated_check(self):
        # Check that the auth_context is in-fact decoded as expected.
        enforcer = rbac_enforcer.enforcer.RBACEnforcer()
        token_path = '/v3/auth/tokens'
        auth_json = self._auth_json()
        with self.test_client() as c:
            r = c.post(token_path, json=auth_json, expected_status_code=201)
            token_id = r.headers.get('X-Subject-Token')
            # NOTE(morgan): The request has to hit the flask app itself before
            # a context is generated. For now, hitting '/' for version
            # discovery does everything we need. This should be changed to
            # a test-specific API eventually.
            c.get('%s/argument/%s' % (self.restful_api_url_prefix,
                                      uuid.uuid4().hex),
                  headers={'X-Auth-Token': token_id})
            enforcer._assert_is_authenticated()
            c.get('/', expected_status_code=300)
            self.assertRaises(exception.Unauthorized,
                              enforcer._assert_is_authenticated)
            oslo_ctx = enforcer._get_oslo_req_context()
            # Set authenticated to a false value that is not None
            oslo_ctx.authenticated = False
            self.assertRaises(exception.Unauthorized,
                              enforcer._assert_is_authenticated)

    def test_extract_policy_check_credentials(self):
        # Make sure extracting the creds is the same as what is in the request
        # environment.
        enforcer = rbac_enforcer.enforcer.RBACEnforcer()
        token_path = '/v3/auth/tokens'
        auth_json = self._auth_json()
        with self.test_client() as c:
            r = c.post(token_path, json=auth_json, expected_status_code=201)
            token_id = r.headers.get('X-Subject-Token')
            # NOTE(morgan): The request has to hit the flask app itself before
            # a context is generated. For now, hitting '/' for version
            # discovery does everything we need. This should be changed to
            # a test-specific API eventually.
            c.get('%s/argument/%s' % (self.restful_api_url_prefix,
                                      uuid.uuid4().hex),
                  headers={'X-Auth-Token': token_id})
            extracted_creds = enforcer._extract_policy_check_credentials(
                uuid.uuid4().hex)
            self.assertEqual(
                flask.request.environ.get(authorization.AUTH_CONTEXT_ENV),
                extracted_creds)

    def test_extract_member_target_data_inferred(self):
        enforcer = rbac_enforcer.enforcer.RBACEnforcer()
        self.restful_api_resource.member_name = 'argument'
        member_from_driver = self.restful_api_resource.get
        self.restful_api_resource.get_member_from_driver = member_from_driver

        argument_id = uuid.uuid4().hex

        with self.test_client() as c:
            c.get('%s/argument/%s' % (self.restful_api_url_prefix,
                                      argument_id))
            extracted = enforcer._extract_member_target_data(
                member_target_type=None, member_target=None)
            self.assertDictEqual(extracted['target'],
                                 self.restful_api_resource().get(argument_id))

    def test_extract_member_target_data_supplied_target(self):
        # Test extract member target data with member_target and
        # member_target_type supplied.
        enforcer = rbac_enforcer.enforcer.RBACEnforcer()
        member_type = uuid.uuid4().hex
        member_target = {uuid.uuid4().hex: {uuid.uuid4().hex}}
        extracted = enforcer._extract_member_target_data(
            member_target_type=member_type, member_target=member_target)
        self.assertDictEqual({'target': {member_type: member_target}},
                             extracted)

    def test_extract_member_target_data_bad_input(self):
        # Test Extract Member Target Data with only "member_target" and only
        # "member_target_type" and ensure empty dict is returned.
        enforcer = rbac_enforcer.enforcer.RBACEnforcer()
        self.assertEqual({}, enforcer._extract_member_target_data(
            member_target=None, member_target_type=uuid.uuid4().hex))
        self.assertEqual({}, enforcer._extract_member_target_data(
            member_target={}, member_target_type=None))

    def test_policy_enforcer_action_decorator(self):

        enforcer = rbac_enforcer.enforcer.RBACEnforcer()

        # Create a method that has an action pre-registered
        action = 'identity:get_user'

        @self.flask_blueprint.route('')
        @enforcer.policy_enforcer_action(action)
        def nothing_interesting():
            return 'OK', 200

        self._register_blueprint_to_app()

        with self.test_client() as c:
            c.get('%s' % self.url_prefix)
            self.assertEqual(action, getattr(g, enforcer.ACTION_STORE_ATTR))

    def test_policy_enforcer_action_invalid_action_decorator(self):
        # If the "action" is not a registered policy enforcement point, check
        # that a ValueError is raised.
        enforcer = rbac_enforcer.enforcer.RBACEnforcer()

        def _decorator_fails():
            # Create a method that has an action pre-registered, but the
            # action is bogus
            action = uuid.uuid4().hex

            @self.flask_blueprint.route('')
            @enforcer.policy_enforcer_action(action)
            def nothing_interesting():
                return 'OK', 200

        self.assertRaises(ValueError, _decorator_fails)

    def test_enforce_call_invalid_action(self):
        enforcer = rbac_enforcer.enforcer.RBACEnforcer()
        self.assertRaises(exception.Unauthorized, enforcer.enforce_call,
                          action=uuid.uuid4().hex)

    def test_enforce_call_not_is_authenticated(self):
        self.skipTest('Test Not Implemented')

    def test_enforce_call_explicit_target_attr(self):
        self.skipTest('Test Not Implemented')

    def test_enforce_call_with_subject_token_data(self):
        self.skipTest('Test Not Implemented')

    def test_enforce_call_passed_member_type_no_member_ref(self):
        self.skipTest('Test Not Implemented')

    def test_enforce_call_passed_member_ref_no_member_type(self):
        self.skipTest('Test Not Implemented')

    def test_enforce_call_inferred_member_target_data(self):
        self.skipTest('Test Not Implemented')

    def test_enforce_call_with_filter_values(self):
        self.skipTest('Test Not Implemented')

    def test_enforce_call_no_filter_values(self):
        self.skipTest('Test Not Implemented')

    def test_enforce_call_with_pre_instantiated_enforcer(self):
        self.skipTest('Test Not Implemented')

    def test_enforce_call_with_auto_instantiated_enforcer(self):
        self.skipTest('Test Not Implemented')

    def test_enforce_call_authorized(self):
        self.skipTest('Test Not Implemented')

    def test_enforce_call_unauthorized(self):
        self.skipTest('Test Not Implemented')
