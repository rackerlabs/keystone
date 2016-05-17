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

from cryptography.fernet import Fernet
from oslo_config import cfg

from keystone.credential import controllers
from keystone.tests import unit
from keystone.tests.unit.ksfixtures import database


CONF = cfg.CONF

_ADMIN_CONTEXT = {
    'is_admin': True,
    'query_string': {},
    'path': '',
    'environment': {
        'wsgi.url_scheme': '',
        'SERVER_NAME': '',
        'SERVER_PORT': ''
    }}


class TestCredentialEncryption(unit.TestCase):

    def setUp(self):
        self.useFixture(database.Database())
        super(TestCredentialEncryption, self).setUp()
        self.load_backends()
        self.credential_controller = controllers.CredentialV3()
        self.credential_api = self.credential_controller.credential_api

    def config_overrides(self):
        super(TestCredentialEncryption, self).config_overrides()
        self.encryption_keys = [Fernet.generate_key(), Fernet.generate_key()]

        self.config_fixture.config(
            group='credential',
            encryption_keys=self.encryption_keys)

    def config_files(self):
        config_files = super(TestCredentialEncryption, self).config_files()
        config_files.append(unit.dirs.tests_conf('backend_sql.conf'))
        return config_files

    def test_create_credential_is_encrypted(self):
        credential = unit.new_credential_ref(user_id=uuid.uuid4().hex)
        created = self.credential_controller.create_credential(
            _ADMIN_CONTEXT, credential)

        credential_id = created['credential']['id']

        encrypted = self.credential_api.get_credential(credential_id)

        retrieved = self.credential_controller.get_credential(
            _ADMIN_CONTEXT, credential_id)

        self.assertNotEqual(created['credential']['blob'], encrypted['blob'])
        self.assertEqual(created, retrieved)

    def test_update_credential_is_encrypted(self):
        credential = unit.new_credential_ref(user_id=uuid.uuid4().hex)
        created = self.credential_controller.create_credential(
            _ADMIN_CONTEXT, credential)

        credential_id = created['credential']['id']

        updated = self.credential_controller.update_credential(
            _ADMIN_CONTEXT, credential_id, {'blob': uuid.uuid4().hex})

        encrypted = self.credential_api.get_credential(credential_id)

        retrieved = self.credential_controller.get_credential(
            _ADMIN_CONTEXT, credential_id)

        self.assertNotEqual(updated['credential']['blob'], encrypted['blob'])
        self.assertEqual(updated, retrieved)

    def test_list_credentials_is_decrypted(self):
        credential = unit.new_credential_ref(user_id=uuid.uuid4().hex)
        created = self.credential_controller.create_credential(
            _ADMIN_CONTEXT, credential)

        credential_id = created['credential']['id']

        encrypted = self.credential_api.get_credential(
            credential_id)

        retrieved = self.credential_controller.list_credentials(
            _ADMIN_CONTEXT)

        self.assertNotEqual(created['credential']['blob'], encrypted['blob'])
        self.assertEqual(created['credential'], retrieved['credentials'][0])
