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

import os
import shutil

from keystone.credential.providers import fernet
from keystone import exception
from keystone.tests import unit
from keystone.tests.unit import ksfixtures
from keystone.tests.unit.ksfixtures import database
import keystone.token.providers.fernet.utils as fernet_utils


class TestFernetCredentialProvider(unit.TestCase):
    def setUp(self):
        super(TestFernetCredentialProvider, self).setUp()
        self.provider = fernet.Provider()
        self.utils = fernet_utils.CredentialUtils()
        self.config_fixture.config(group='credential', max_active_keys=3)
        self.useFixture(database.Database())
        self.useFixture(ksfixtures.CredentialRepository(self.config_fixture))
        shutil.rmtree(self.provider.utils.key_repository)
        os.mkdir(self.provider.utils.key_repository)

    def config_overrides(self):
        super(TestFernetCredentialProvider, self).config_overrides()

    def test_valid_data_encryption(self):
        self.utils.initialize_key_repository()
        self.utils.rotate_keys()

        blob = 'blob'
        token = self.provider.encrypt(blob)
        decrypted_blob = self.provider.decrypt(token)

        self.assertNotEqual(blob, token)
        self.assertEqual(blob, decrypted_blob)

    def test_encrypt_with_invalid_key_raises_exception_without_allow_plaintext(
            self):
        self.config_fixture.config(
            group='credential',
            allow_plaintext=False)

        self.assertRaises(exception.CredentialEncryptionError,
                          self.provider.encrypt, 'blob')

    def test_encrypt_with_invalid_key_returns_data_with_allow_plaintext(self):
        blob = 'blob'
        self.config_fixture.config(
            group='credential',
            allow_plaintext=True)

        token = self.provider.encrypt(blob)
        self.assertEqual(blob, token)

    def test_decrypt_with_invalid_key_raises_exception_without_allow_plaintext(
            self):
        self.config_fixture.config(
            group='credential',
            allow_plaintext=False)

        self.assertRaises(exception.CredentialEncryptionError,
                          self.provider.decrypt, 'blob')

    def test_decrypt_with_invalid_key_returns_data_with_allow_plaintext(self):
        blob = 'blob'
        self.config_fixture.config(
            group='credential',
            allow_plaintext=True)

        data = self.provider.decrypt(blob)
        self.assertEqual(blob, data)
