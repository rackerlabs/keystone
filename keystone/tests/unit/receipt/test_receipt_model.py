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

import copy
import uuid

from oslo_utils import timeutils

from keystone.models import receipt_model
from keystone.tests.unit import core
from keystone.tests.unit import test_receipt_provider


class TestKeystoneReceiptModel(core.TestCase):
    def setUp(self):
        super(TestKeystoneReceiptModel, self).setUp()
        self.v3_sample_receipt = copy.deepcopy(
            test_receipt_provider.SAMPLE_V3_RECEIPT)

    def test_receipt_model_v3(self):
        receipt_data = receipt_model.KeystoneReceipt(
            uuid.uuid4().hex, self.v3_sample_receipt)
        expires = timeutils.normalize_time(timeutils.parse_isotime(
            self.v3_sample_receipt['receipt']['expires_at']))
        issued = timeutils.normalize_time(timeutils.parse_isotime(
            self.v3_sample_receipt['receipt']['issued_at']))
        self.assertEqual(expires, receipt_data.expires)
        self.assertEqual(issued, receipt_data.issued)
        self.assertEqual(self.v3_sample_receipt['receipt']['methods'],
                         receipt_data.methods)
        self.assertEqual(self.v3_sample_receipt['receipt']['user']['id'],
                         receipt_data.user_id)
        self.assertEqual(self.v3_sample_receipt['receipt']['user']['name'],
                         receipt_data.user_name)
        self.assertEqual(
            self.v3_sample_receipt['receipt']['user']['domain']['id'],
            receipt_data.user_domain_id)
        self.assertEqual(
            self.v3_sample_receipt['receipt']['user']['domain']['name'],
            receipt_data.user_domain_name)
