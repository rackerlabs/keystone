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

import keystone.conf
from keystone.credential import controllers
from keystone.tests import unit
from keystone.tests.unit import ksfixtures
from keystone.tests.unit.ksfixtures import database
from keystone.token.providers.fernet.utils import CredentialUtils


CONF = keystone.conf.CONF


class TestCredentialEncryption(unit.TestCase):

    def setUp(self):
        self.useFixture(database.Database())
        super(TestCredentialEncryption, self).setUp()
        self.load_backends()
        self.credential_controller = controllers.CredentialV3()
        self.credential_api = self.credential_controller.credential_api
        self.config_fixture.config(group='credential', max_active_keys=2)
        self.useFixture(ksfixtures.CredentialRepository(self.config_fixture))
        self.utils = CredentialUtils()
        self.utils.initialize_key_repository()
        self.utils.rotate_keys()

    def test_create_credential_is_encrypted(self):
        credential = unit.new_credential_ref(user_id=uuid.uuid4().hex)
        created = self.credential_controller.create_credential(
            self.make_request(is_admin=True), credential)

        credential_id = created['credential']['id']

        encrypted = self.credential_api.get_credential(credential_id)

        retrieved = self.credential_controller.get_credential(
            self.make_request(is_admin=True), credential_id)

        self.assertNotEqual(created['credential']['blob'], encrypted['blob'])
        self.assertEqual(created, retrieved)

    def test_update_credential_is_encrypted(self):
        credential = unit.new_credential_ref(user_id=uuid.uuid4().hex)
        created = self.credential_controller.create_credential(
            self.make_request(is_admin=True), credential)

        credential_id = created['credential']['id']

        updated = self.credential_controller.update_credential(
            self.make_request(is_admin=True),
            credential_id, {'blob': uuid.uuid4().hex})

        encrypted = self.credential_api.get_credential(credential_id)

        retrieved = self.credential_controller.get_credential(
            self.make_request(is_admin=True), credential_id)

        self.assertNotEqual(updated['credential']['blob'], encrypted['blob'])
        self.assertEqual(updated, retrieved)

    def test_list_credentials_is_decrypted(self):
        credential = unit.new_credential_ref(user_id=uuid.uuid4().hex)
        created = self.credential_controller.create_credential(
            self.make_request(is_admin=True), credential)

        credential_id = created['credential']['id']

        encrypted = self.credential_api.get_credential(
            credential_id)

        retrieved = self.credential_controller.list_credentials(
            self.make_request(is_admin=True))

        self.assertNotEqual(created['credential']['blob'], encrypted['blob'])
        self.assertEqual(created['credential'], retrieved['credentials'][0])

    def test_create_credential_returns_unencrypted(self):
        credential = unit.new_credential_ref(user_id=uuid.uuid4().hex)
        created = self.credential_controller.create_credential(
            self.make_request(is_admin=True), credential)

        self.assertEqual(created['credential']['blob'], credential['blob'])

    def test_update_credential_returns_unencrypted(self):
        credential = unit.new_credential_ref(user_id=uuid.uuid4().hex)
        created = self.credential_controller.create_credential(
            self.make_request(is_admin=True), credential)

        credential_id = created['credential']['id']
        updated_blob = uuid.uuid4().hex

        updated = self.credential_controller.update_credential(
            self.make_request(is_admin=True),
            credential_id, {'blob': updated_blob})

        self.assertEqual(updated['credential']['blob'], updated_blob)
