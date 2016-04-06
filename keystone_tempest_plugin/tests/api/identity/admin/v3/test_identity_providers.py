# Copyright 2016 Red Hat, Inc.
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

from keystone_tempest_plugin.tests.api.identity import base
from tempest.common.utils import data_utils
from tempest import test


class IndentityProvidersTest(base.BaseIdentityV3AdminTest):

    def _check_identity_provider(self, idp):
        self.assertIn('id', idp)

        # Check the optional attributes have been set
        self.assertIn('description', idp)
        self.assertIn('enabled', idp)
        self.assertIn('remote_ids', idp)

    @test.idempotent_id('09450910-b816-4150-8513-a2fd4628a0c3')
    def test_identity_provider_create(self):
        idp_id = data_utils.rand_uuid_hex()
        idp = self.identity_providers_client.create_identity_provider(
            idp_id)['identity_provider']
        self.addCleanup(
            self.identity_providers_client.delete_identity_provider, idp_id)

        self._check_identity_provider(idp)

        # The identity provider is disabled by default
        self.assertFalse(idp['enabled'])

    @test.idempotent_id('f430a337-545d-455e-bb6c-cb0fdf4be5c1')
    def test_identity_provider_create_with_enabled_true(self):
        idp_id = data_utils.rand_uuid_hex()
        idp = self.identity_providers_client.create_identity_provider(
            idp_id, enabled=True)['identity_provider']
        self.addCleanup(
            self.identity_providers_client.delete_identity_provider, idp_id)

        self._check_identity_provider(idp)

        # The identity provider should be enabled
        self.assertTrue(idp['enabled'])

    @test.idempotent_id('238e6163-d600-4f59-9982-c621f057221d')
    def test_identity_provider_create_with_remote_ids(self):
        idp_id = data_utils.rand_uuid_hex()
        remote_ids = ['remote_id1', 'remote_id2']
        idp = self.identity_providers_client.create_identity_provider(
            idp_id, enabled=True, remote_ids=remote_ids)['identity_provider']
        self.addCleanup(
            self.identity_providers_client.delete_identity_provider, idp_id)

        self._check_identity_provider(idp)
        for remote_id in remote_ids:
            self.assertIn(remote_id, idp['remote_ids'])

    @test.idempotent_id('8a7817ad-27f8-436b-9cbe-46aa20989beb')
    def test_identity_provider_get(self):
        idp_id = data_utils.rand_uuid_hex()
        self.identity_providers_client.create_identity_provider(
            idp_id, enabled=True)['identity_provider']
        self.addCleanup(
            self.identity_providers_client.delete_identity_provider, idp_id)

        idp_get = self.identity_providers_client.show_identity_provider(
            idp_id)['identity_provider']
        self.assertEqual(idp_id, idp_get['id'])
        self._check_identity_provider(idp_get)

    @test.idempotent_id('cbfe5de9-c58a-4810-950c-2acdf985879d')
    def test_identity_provider_list(self):
        idp_ids = []
        for _ in range(3):
            idp_id = data_utils.rand_uuid_hex()
            self.identity_providers_client.create_identity_provider(
                idp_id, enabled=True)['identity_provider']
            self.addCleanup(
                self.identity_providers_client.delete_identity_provider,
                idp_id)
            idp_ids.append(idp_id)

        idp_list = self.identity_providers_client.list_identity_providers()[
            'identity_providers']
        fetched_ids = [fetched_idp['id'] for fetched_idp in idp_list]

        for idp_id in idp_ids:
            self.assertIn(idp_id, fetched_ids)

    @test.idempotent_id('36a0d9f0-9517-4139-85d0-f78d905aece5')
    def test_identity_provider_update(self):
        idp_id = data_utils.rand_uuid_hex()
        idp = self.identity_providers_client.create_identity_provider(
            idp_id, enabled=True)['identity_provider']
        self.addCleanup(
            self.identity_providers_client.delete_identity_provider, idp_id)

        # The identity provider should be enabled
        self.assertTrue(idp['enabled'])

        idp = self.identity_providers_client.update_identity_provider(
            idp_id, enabled=False)['identity_provider']

        # The identity provider should be disabled
        self.assertFalse(idp['enabled'])
