# Copyright 2013 OpenStack Foundation
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

import datetime

from oslo_utils import timeutils

from keystone.common import provider_api
from keystone.common import utils
import keystone.conf
from keystone import exception
from keystone import receipt
from keystone.tests import unit
from keystone.tests.unit import ksfixtures
from keystone.tests.unit.ksfixtures import database


CONF = keystone.conf.CONF
PROVIDERS = provider_api.ProviderAPIs

FUTURE_DELTA = datetime.timedelta(seconds=CONF.receipt.expiration)
CURRENT_DATE = timeutils.utcnow()

SAMPLE_V3_RECEIPT = {
    'receipt': {
        'methods': ['password'],
        'user': {
            'id': '2c58febd6903463584a75206ee6ea658',
            'name': 'bbaccf7403fb48c8a726c49d7177d765',
            'domain': {
                'id': '70d173f0a41a484d977b71a779836282',
                'name': 'd99a05d759904d4cb89826e4d83d19be'
            }
        },
        'expires_at': '2018-06-29T02:41:48.000000Z',
        'issued_at': '2018-06-29T02:36:48.000000Z'
    }
}


def create_v3_receipt():
    return {
        "receipt": {
            'methods': [],
            "expires_at": utils.isotime(timeutils.utcnow() + FUTURE_DELTA),
            "issued_at": "2013-05-21T00:02:43.941473Z",
        }
    }


SAMPLE_V3_RECEIPT_EXPIRED = {
    "receipt": {
        "expires_at": utils.isotime(CURRENT_DATE),
        "issued_at": "2013-05-21T00:02:43.941473Z",
    }
}

SAMPLE_MALFORMED_RECEIPT = {
    "receipt": {
        "bogus": {
            "no expiration data": None
        }
    }
}


class TestReceiptProvider(unit.TestCase):
    def setUp(self):
        super(TestReceiptProvider, self).setUp()
        self.useFixture(database.Database())
        self.useFixture(
            ksfixtures.KeyRepository(
                self.config_fixture,
                'fernet_receipts',
                CONF.fernet_receipts.max_active_keys
            )
        )
        self.load_backends()

    def test_unsupported_receipt_provider(self):
        self.config_fixture.config(group='receipt',
                                   provider='MyProvider')
        self.assertRaises(ImportError,
                          receipt.provider.Manager)

    def test_provider_receipt_expiration_validation(self):
        self.assertRaises(exception.ReceiptNotFound,
                          PROVIDERS.receipt_provider_api._is_valid_receipt,
                          SAMPLE_V3_RECEIPT_EXPIRED)
        self.assertRaises(exception.ReceiptNotFound,
                          PROVIDERS.receipt_provider_api._is_valid_receipt,
                          SAMPLE_MALFORMED_RECEIPT)
        self.assertIsNone(
            PROVIDERS.receipt_provider_api._is_valid_receipt(
                create_v3_receipt()))

    def test_validate_v3_none_receipt_raises_receipt_not_found(self):
        self.assertRaises(
            exception.ReceiptNotFound,
            PROVIDERS.receipt_provider_api.validate_receipt,
            None)
