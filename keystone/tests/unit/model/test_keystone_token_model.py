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

from keystone import exception
from keystone.models import token_model
from keystone.openstack.common import timeutils
from keystone import tests
from keystone.tests import default_fixtures


class KeystoneTokenModelDescriptorTests(tests.TestCase):

    def setUp(self):
        super(KeystoneTokenModelDescriptorTests, self).setUp()
        self.load_backends()
        self.token_model = token_model.KeystoneTokenModel(
            is_admin=False, includes_catalog=False)
        self.domain = self.assignment_api.create_domain(
            default_fixtures.DOMAINS[0]['id'],
            default_fixtures.DOMAINS[0])
        self.project = self.assignment_api.create_project(
            default_fixtures.TENANTS[0]['id'],
            default_fixtures.TENANTS[0])
        self.addCleanup(self.cleanup_instance('domain', 'token_model'))

    def test_token_model_default_expires_at_desc(self):
        time = timeutils.utcnow()
        self.assertGreater(self.token_model.expires_at, time)

    def test_token_model_set_expires_at_desc(self):
        time = timeutils.utcnow()
        self.token_model.expires_at = time
        self.assertEqual(time, self.token_model.expires_at)

    def test_token_model_from_primitive_expires_at_desc(self):
        time = timeutils.utcnow()
        token_model.KeystoneTokenModel.expires_at.from_primitive(
            self.token_model,
            timeutils.isotime(time, subsecond=True))
        self.assertEqual(time, self.token_model.expires_at)

    def test_token_model_to_primitive_expires_at_desc(self):
        time = timeutils.utcnow()
        self.token_model.expires_at = time
        self.assertEqual(
            timeutils.isotime(time, subsecond=True),
            token_model.KeystoneTokenModel.expires_at.to_primitive(
                self.token_model))

    def test_token_model_default_issued_at_desc(self):
        time = timeutils.utcnow()
        self.assertGreater(self.token_model.issued_at, time)

    def test_token_model_set_issued_at_desc(self):
        time = timeutils.utcnow()
        self.token_model.issued_at = time
        self.assertEqual(time, self.token_model.issued_at)

    def test_token_model_from_primitive_issued_at_desc(self):
        time = timeutils.utcnow()
        token_model.KeystoneTokenModel.issued_at.from_primitive(
            self.token_model,
            timeutils.isotime(time, subsecond=True))
        self.assertEqual(time, self.token_model.issued_at)

    def test_token_model_to_primitive_issued_at_desc(self):
        time = timeutils.utcnow()
        self.token_model.issued_at = time
        self.assertEqual(
            timeutils.isotime(time, subsecond=True),
            token_model.KeystoneTokenModel.issued_at.to_primitive(
                self.token_model))

    def test_token_model_default_domain_desc(self):
        self.assertIsNone(self.token_model.domain)

    def test_token_model_set_domain_desc(self):
        self.token_model.domain = self.domain['id']
        self.assertEqual(self.domain['id'], self.token_model.domain['id'])
        self.assertEqual(self.domain['name'], self.token_model.domain['name'])
        self.assertNotIn('description', self.token_model.domain)
        # Ensure the dict containing the domain information is immutable
        self.assertRaises(TypeError, self.token_model.domain.__setitem__,
                          'id', 'NotAllowed')

    def test_token_model_from_primitive_domain_desc(self):
        pass

    def test_token_model_to_primitive_domain_desc(self):
        pass

    def test_token_model_default_project_desc(self):
        self.assertIsNone(self.token_model.project)

    def test_token_model_set_project_desc(self):
        pass

    def test_token_model_from_primitive_project_desc(self):
        pass

    def test_token_model_to_primitive_project_desc(self):
        pass

    def test_token_model_default_oauth_desc(self):
       self.assertIsNone(self.token_model.oauth)

    def test_token_model_set_oauth_desc(self):
        pass

    def test_token_model_from_primitive_oauth_desc(self):
        pass

    def test_token_model_to_primitive_oauth_desc(self):
        pass

    def test_token_model_default_trust_desc(self):
       self.assertIsNone(self.token_model.trust)

    def test_token_model_set_trust_desc(self):
        pass

    def test_token_model_from_primitive_trust_desc(self):
        pass

    def test_token_model_to_primitive_trust_desc(self):
        pass

    def test_token_model_default_user_desc(self):
       self.assertIsNone(self.token_model.user)

    def test_token_model_set_user_desc(self):
        pass

    def test_token_model_from_primitive_user_desc(self):
        pass

    def test_token_model_to_primitive_user_desc(self):
        pass


class KeystoneTokenModelTests(tests.TestCase):

    def setUp(self):
        super(KeystoneTokenModelTests, self).setUp()

    def test_token_model_frozen(self):
        pass

    def test_token_model_set_token_id(self):
        pass

    def test_token_model_to_primitive_from_primitive(self):
        pass

