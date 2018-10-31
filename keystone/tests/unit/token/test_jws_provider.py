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

from keystone.common import provider_api
import keystone.conf
from keystone import exception
from keystone.tests import unit
from keystone.tests.unit import ksfixtures
from keystone.token.providers import jws

CONF = keystone.conf.CONF
PROVIDERS = provider_api.ProviderAPIs


class TestJWSProvider(unit.TestCase):

    def setUp(self):
        super(TestJWSProvider, self).setUp()
        self.config_fixture.config(group='token', provider='jws')
        self.useFixture(ksfixtures.JWSKeyRepository(self.config_fixture))
        self.provider = jws.Provider()

    def test_invalid_token_raises_token_not_found(self):
        token_id = uuid.uuid4().hex
        self.assertRaises(
            exception.TokenNotFound,
            self.provider.validate_token,
            token_id
        )
