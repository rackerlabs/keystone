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

from cryptography.fernet import Fernet

from keystone.credential.providers import fernet
from keystone import exception
from keystone.tests import unit
from keystone.tests.unit.ksfixtures import database


class TestFernetCredentialProvider(unit.TestCase):
    def setUp(self):
        super(TestFernetCredentialProvider, self).setUp()
        self.provider = fernet.Provider()
        self.useFixture(database.Database())

    def config_overrides(self):
        super(TestFernetCredentialProvider, self).config_overrides()
        self.encryption_keys = [Fernet.generate_key(), Fernet.generate_key()]

        self.config_fixture.config(
            group='credential',
            encryption_keys=self.encryption_keys)

    def test_get_encryption_keys(self):
        self.assertEqual(self.provider._get_encryption_keys(),
                         self.encryption_keys)

    def test_get_active_key(self):
        self.assertEqual(self.provider._get_active_key(),
                         self.encryption_keys[0])

    def test_valid_data_encryption(self):
        blob = 'blob'
        token = self.provider.encrypt(blob)
        decrypted_blob = self.provider.decrypt(token)

        self.assertNotEqual(blob, token)
        self.assertEqual(blob, decrypted_blob)

    def test_encrypt_with_invalid_key_raises_exception(self):
        self.config_fixture.config(
            group='credential',
            encryption_keys=[],
            allow_plaintext=False)

        self.assertRaises(exception.Error, self.provider.encrypt, 'blob')

    def test_encrypt_with_invalid_key_returns_data(self):
        blob = 'blob'
        self.config_fixture.config(
            group='credential',
            encryption_keys=[],
            allow_plaintext=True)

        token = self.provider.encrypt(blob)
        self.assertEqual(blob, token)

    def test_decrypt_with_invalid_key_raises_exception(self):
        self.config_fixture.config(
            group='credential',
            encryption_keys=[],
            allow_plaintext=False)

        self.assertRaises(exception.Error, self.provider.decrypt, 'blob')

    def test_decrypt_with_invalid_key_returns_data(self):
        blob = 'blob'
        self.config_fixture.config(
            group='credential',
            encryption_keys=[],
            allow_plaintext=True)

        data = self.provider.decrypt(blob)
        self.assertEqual(blob, data)
