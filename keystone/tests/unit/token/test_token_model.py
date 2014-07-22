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

from keystone.common import config
from keystone import exception
from keystone.openstack.common import timeutils
from keystone.tests import core
from keystone.tests import test_token_provider
from keystone.token import model


CONF = config.CONF
SAMPLE_V3_TOKEN = test_token_provider.SAMPLE_V3_TOKEN
SAMPLE_V2_TOKEN = test_token_provider.SAMPLE_V2_TOKEN


class TestKeystoneTokenModel(core.TestCase):
    def setUp(self):
        super(TestKeystoneTokenModel, self).setUp()
        self.load_backends()

    def test_token_model_v3(self):
        token_data = model.KeystoneToken(uuid.uuid4().hex, SAMPLE_V3_TOKEN)
        self.assertIs(model.V3, token_data.version)
        expires = timeutils.normalize_time(timeutils.parse_isotime(
            SAMPLE_V3_TOKEN['token']['expires_at']))
        issued = timeutils.normalize_time(timeutils.parse_isotime(
            SAMPLE_V3_TOKEN['token']['issued_at']))
        self.assertEqual(expires, token_data.expires)
        self.assertEqual(issued, token_data.issued)
        self.assertEqual(SAMPLE_V3_TOKEN['token']['user']['id'],
                         token_data.user_id)
        self.assertEqual(SAMPLE_V3_TOKEN['token']['user']['name'],
                         token_data.user_name)
        self.assertEqual(SAMPLE_V3_TOKEN['token']['user']['domain']['id'],
                         token_data.user_domain_id)
        self.assertEqual(SAMPLE_V3_TOKEN['token']['user']['domain']['name'],
                         token_data.user_domain_name)
        self.assertEqual(SAMPLE_V3_TOKEN['token']['project']['domain']['id'],
                         token_data.project_domain_id)
        self.assertEqual(SAMPLE_V3_TOKEN['token']['project']['domain']['name'],
                         token_data.project_domain_name)
        self.assertEqual(SAMPLE_V3_TOKEN['token']['OS-TRUST:trust']['id'],
                         token_data.trust_id)
        self.assertEqual(
            SAMPLE_V3_TOKEN['token']['OS-TRUST:trust']['trustor_user_id'],
            token_data.trustor_user_id)
        self.assertEqual(
            SAMPLE_V3_TOKEN['token']['OS-TRUST:trust']['trustee_user_id'],
            token_data.trustee_user_id)
        # Project Scoped Token
        self.assertIsNone(token_data.domain_id)
        self.assertIsNone(token_data.domain_name)
        self.assertFalse(token_data.domain_scoped)
        self.assertEqual(SAMPLE_V3_TOKEN['token']['project']['id'],
                         token_data.project_id)
        self.assertEqual(SAMPLE_V3_TOKEN['token']['project']['name'],
                         token_data.project_name)
        self.assertTrue(token_data.project_scoped)
        self.assertTrue(token_data.scoped)
        self.assertTrue(token_data.trust_scoped)
        self.assertEqual([r['id'] for r in SAMPLE_V3_TOKEN['token']['roles']],
                         token_data.role_ids)
        self.assertEqual(
            [r['name'] for r in SAMPLE_V3_TOKEN['token']['roles']],
            token_data.role_names)

    def test_token_model_v2(self):
        token_data = model.KeystoneToken(uuid.uuid4().hex, SAMPLE_V2_TOKEN)
        self.assertIs(model.V2, token_data.version)
        expires = timeutils.normalize_time(timeutils.parse_isotime(
            SAMPLE_V2_TOKEN['access']['token']['expires']))
        issued = timeutils.normalize_time(timeutils.parse_isotime(
            SAMPLE_V2_TOKEN['access']['token']['issued_at']))
        self.assertEqual(expires, token_data.expires)
        self.assertEqual(issued, token_data.issued)
        self.assertEqual(SAMPLE_V2_TOKEN['access']['user']['id'],
                         token_data.user_id)
        self.assertEqual(SAMPLE_V2_TOKEN['access']['user']['name'],
                         token_data.user_name)
        self.assertIsNone(token_data.user_domain_id)
        self.assertIsNone(token_data.user_domain_name)
        self.assertEqual(CONF.identity.default_domain_id,
                         token_data.project_domain_id)
        self.assertEqual('Default',
                         token_data.project_domain_name)
        self.assertEqual(SAMPLE_V2_TOKEN['access']['trust']['id'],
                         token_data.trust_id)
        self.assertIsNone(token_data.trustor_user_id)
        self.assertEqual(
            SAMPLE_V2_TOKEN['access']['trust']['trustee_user_id'],
            token_data.trustee_user_id)
        # Project Scoped Token
        self.assertIsNone(token_data.domain_id)
        self.assertIsNone(token_data.domain_name)
        self.assertFalse(token_data.domain_scoped)
        self.assertEqual(SAMPLE_V2_TOKEN['access']['token']['tenant']['id'],
                         token_data.project_id)
        self.assertEqual(SAMPLE_V2_TOKEN['access']['token']['tenant']['name'],
                         token_data.project_name)
        self.assertTrue(token_data.project_scoped)
        self.assertTrue(token_data.scoped)
        self.assertTrue(token_data.trust_scoped)
        self.assertEqual(
            [r['name'] for r in SAMPLE_V2_TOKEN['access']['user']['roles']],
            token_data.role_names)

    def test_token_model_unknown(self):
        self.assertRaises(exception.UnsupportedTokenVersionException,
                          model.KeystoneToken,
                          token_id=uuid.uuid4().hex,
                          token_data={'bogus_data': uuid.uuid4().hex})
