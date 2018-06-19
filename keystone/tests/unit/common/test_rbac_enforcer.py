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

from oslo_config import fixture as config_fixture
import flask
from flask import blueprints

from keystone.common import rbac_enforcer
import keystone.conf
from keystone.server.flask import common as flask_common
from keystone.tests import unit
from keystone.tests.unit import rest


class TestRBACEnforcer(unit.TestCase):

    def test_enforcer_shared_state(self):
        enforcer = rbac_enforcer.enforcer.RBACEnforcer()
        enforcer2 = rbac_enforcer.enforcer.RBACEnforcer()

        self.assertIsNotNone(enforcer._enforcer)
        self.assertEqual(enforcer._enforcer, enforcer2._enforcer)
        setattr(enforcer, '_test_attr', uuid.uuid4().hex)
        self.assertEqual(enforcer._test_attr, enforcer2._test_attr)


class TestRBACEnforcerRest(rest.RestfulTestCase):

    def setUp(self):
        super(TestRBACEnforcerRest, self).setUp()
        self._setup_dynmic_flask_blueprint_API()

    def _setup_dynmic_flask_blueprint_API(self):
        # Create a dynamic flask blueprint with a known prefix
        api = uuid.uuid4().hex
        url_prefix = '/_%s_TEST' % api
        blueprint = blueprints.Blueprint(api, __name__, url_prefix=url_prefix)
        # TODO(morgan): remove the need for webtest, but for now just unwrap
        # by one layer.
        self.public_app.app.register_blueprint(blueprint)
        self.url_prefix = url_prefix
        self.flask_blueprint = blueprint
        self.cleanup_instance('flask_blueprint', 'url_prefix')

    def test_extract_subject_token_target_data(self):
        pass

    def test_extract_filter_data(self):
        # Test that we are extracting useful filter data from the
        # request context.

        path = uuid.uuid4().hex

        @self.flask_blueprint.route('/%s' % path)
        def get():
            return {}

        with self.public_app.app.test_client() as c:
            expected_param = uuid.uuid4().hex
            unexpected_param = uuid.uuid4().hex
            get_path = '/'.join([self.url_prefix, path])
            qs = '%(expected)s=EXPECTED&%(unexpected)s=UNEXPECTED' % {
                'expected': expected_param,
                'unexpected': unexpected_param
            }

            c.get('%(path)s?%(qs)s' % {'path': get_path, 'qs': qs})
            enforcer = rbac_enforcer.enforcer.RBACEnforcer()
            extracted_filter = enforcer._extract_filter_values(
                [expected_param])
            self.assertNotIn(extracted_filter, unexpected_param)
            self.assertIn(expected_param, expected_param)
            self.assertEqual(extracted_filter[expected_param], 'EXPECTED')

    def test_retriving_oslo_req_context(self):
        pass

    def test_is_admin_check(self):
        pass

    def test_is_authenticated_check(self):
        pass

    def test_extract_policy_check_credentials(self):
        pass

    def test_extract_member_target_data(self):
        pass

    def test_enforcer_auto_instantiated(self):
        pass

    def test_policy_enforcer_action_decorator(self):
        pass

    def test_policy_enforcer_action_invalid_action_decorator(self):
        pass

    def test_enforce_call_invalid_action(self):
        pass

    def test_enforce_call_is_admin(self):
        pass

    def test_enforce_call_not_is_authenticated(self):
        pass

    def test_enforce_call_explicit_target_attr(self):
        pass

    def test_enforce_call_with_subject_token_data(self):
        pass

    def test_enforce_call_passed_member_type_no_member_ref(self):
        pass

    def test_enforce_call_passed_member_ref_no_member_type(self):
        pass

    def test_enforce_call_inferred_member_target_data(self):
        pass

    def test_enforce_call_with_filter_values(self):
        pass

    def test_enforce_call_no_filter_values(self):
        pass

    def test_enforce_call_with_pre_instantiated_enforcer(self):
        pass

    def test_enforce_call_with_auto_instantiated_enforcer(self):
        pass

    def test_enforce_call_authorized(self):
        pass

    def test_enforce_call_unauthorized(self):
        pass

