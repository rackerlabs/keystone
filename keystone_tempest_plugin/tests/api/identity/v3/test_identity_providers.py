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
from keystone_tempest_plugin.tests.api.identity.v3 import fixtures

from tempest.lib.common.utils import data_utils
from tempest import test


class IndentityProvidersTest(base.BaseIdentityV3Test):

    def setUp(self):
        super(IndentityProvidersTest, self).setUp()
        self.identity_providers_client.set_test_case(self)
        self.mapping_rules_client.set_test_case(self)

    def _assert_identity_provider_attributes(self, idp, idp_id, idp_ref=None):
        self.assertIn('id', idp)
        self.assertEqual(idp_id, idp['id'])

        # Check the optional attributes have been set
        self.assertIn('description', idp)
        self.assertIn('enabled', idp)
        self.assertIn('remote_ids', idp)

        if idp_ref:
            self.assertEqual(idp_ref['description'], idp['description'])

            if 'enabled' in idp_ref:
                self.assertEqual(idp_ref['enabled'], idp['enabled'])

            if 'remote_ids' in idp_ref:
                self.assertItemsEqual(idp_ref['remote_ids'], idp['remote_ids'])

    def _assert_protocol_attributes(self, protocol, protocol_id,
                                    mapping_id=None):
        self.assertIn('id', protocol)
        self.assertEqual(protocol_id, protocol['id'])

        self.assertIn('mapping_id', protocol)
        if mapping_id:
            self.assertEqual(mapping_id, protocol['mapping_id'])

    @test.idempotent_id('09450910-b816-4150-8513-a2fd4628a0c3')
    def test_identity_provider_create(self):
        idp_id = data_utils.rand_uuid_hex()
        idp_ref = fixtures.idp_ref()
        idp = self.identity_providers_client.create_identity_provider(
            idp_id, **idp_ref)

        # The identity provider is disabled by default
        idp_ref['enabled'] = False

        # The remote_ids attribute should be set to an empty list by default
        idp_ref['remote_ids'] = []

        self._assert_identity_provider_attributes(idp, idp_id, idp_ref)

    @test.idempotent_id('f430a337-545d-455e-bb6c-cb0fdf4be5c1')
    def test_identity_provider_create_with_enabled_true(self):
        idp_id = data_utils.rand_uuid_hex()
        idp_ref = fixtures.idp_ref(enabled=True)
        idp = self.identity_providers_client.create_identity_provider(
            idp_id, **idp_ref)

        self._assert_identity_provider_attributes(idp, idp_id, idp_ref)

    @test.idempotent_id('238e6163-d600-4f59-9982-c621f057221d')
    def test_identity_provider_create_with_remote_ids(self):
        idp_id = data_utils.rand_uuid_hex()
        remote_ids = [data_utils.rand_uuid_hex(), data_utils.rand_uuid_hex()]
        idp_ref = fixtures.idp_ref(remote_ids=remote_ids)
        idp = self.identity_providers_client.create_identity_provider(
            idp_id, **idp_ref)

        self._assert_identity_provider_attributes(idp, idp_id, idp_ref)

    @test.idempotent_id('8a7817ad-27f8-436b-9cbe-46aa20989beb')
    def test_identity_provider_get(self):
        idp_id = data_utils.rand_uuid_hex()
        idp_create = self.identity_providers_client.create_identity_provider(
            idp_id)

        idp_get = self.identity_providers_client.show_identity_provider(
            idp_id)
        self._assert_identity_provider_attributes(idp_get, idp_id, idp_create)

    @test.idempotent_id('cbfe5de9-c58a-4810-950c-2acdf985879d')
    def test_identity_provider_list(self):
        idp_ids = []
        for _ in range(3):
            idp_id = data_utils.rand_uuid_hex()
            self.identity_providers_client.create_identity_provider(
                idp_id, enabled=True)
            idp_ids.append(idp_id)

        idp_list = self.identity_providers_client.list_identity_providers()
        fetched_ids = [fetched_idp['id'] for fetched_idp in idp_list]

        for idp_id in idp_ids:
            self.assertIn(idp_id, fetched_ids)

    @test.idempotent_id('36a0d9f0-9517-4139-85d0-f78d905aece5')
    def test_identity_provider_update(self):
        idp_id = data_utils.rand_uuid_hex()
        idp = self.identity_providers_client.create_identity_provider(
            idp_id, **fixtures.idp_ref(enabled=True))

        # The identity provider should be enabled
        self.assertTrue(idp['enabled'])

        idp = self.identity_providers_client.update_identity_provider(
            idp_id, enabled=False)

        # The identity provider should be disabled
        self.assertFalse(idp['enabled'])

    def _create_identity_provider_and_mapping(self):
        # Create an identity provider
        idp_id = data_utils.rand_uuid_hex()
        self.identity_providers_client.create_identity_provider(
            idp_id, **fixtures.idp_ref(enabled=True))

        # Create a mapping rule
        mapping_id = data_utils.rand_uuid_hex()
        self.mapping_rules_client.create_mapping_rule(
            mapping_id, fixtures.mapping_ref())

        return idp_id, mapping_id

    def test_add_protocol_to_identity_provider(self):
        idp_id, mapping_id = self._create_identity_provider_and_mapping()

        # Now we try to add a protocol to the identity provider
        protocol_id = data_utils.rand_uuid_hex()
        protocol = self.identity_providers_client.add_protocol_and_mapping(
            idp_id, protocol_id, mapping_id)

        self._assert_protocol_attributes(protocol, protocol_id, mapping_id)

    def test_get_protocol_from_identity_provider(self):
        idp_id, mapping_id = self._create_identity_provider_and_mapping()

        # Add a protocol to the identity provider
        protocol_id = data_utils.rand_uuid_hex()
        self.identity_providers_client.add_protocol_and_mapping(
            idp_id, protocol_id, mapping_id)

        # Try to get the protocol
        protocol = self.identity_providers_client.get_protocol_and_mapping(
            idp_id, protocol_id)
        self._assert_protocol_attributes(protocol, protocol_id, mapping_id)

    def test_list_protocols_from_identity_provider(self):
        idp_id, mapping_id = self._create_identity_provider_and_mapping()

        protocol_ids = []
        for _ in range(3):
            protocol_id = data_utils.rand_uuid_hex()
            self.identity_providers_client.add_protocol_and_mapping(
                idp_id, protocol_id, mapping_id)
            protocol_ids.append(protocol_id)

        protocols_list = (
            self.identity_providers_client.list_protocols_and_mappings(idp_id))
        fetched_ids = [fetched['id'] for fetched in protocols_list]

        for protocol_id in protocol_ids:
            self.assertIn(protocol_id, fetched_ids)

    def test_update_mapping_from_identity_provider_protocol(self):
        idp_id, mapping_id = self._create_identity_provider_and_mapping()

        # Add a protocol to the identity provider
        protocol_id = data_utils.rand_uuid_hex()
        self.identity_providers_client.add_protocol_and_mapping(
            idp_id, protocol_id, mapping_id)

        # Create another mapping
        new_mapping_id = data_utils.rand_uuid_hex()
        self.mapping_rules_client.create_mapping_rule(
            new_mapping_id, fixtures.mapping_ref())

        # Update the identity provider protocol
        protocol = self.identity_providers_client.update_protocol_mapping(
            idp_id, protocol_id, new_mapping_id)

        self._assert_protocol_attributes(protocol, protocol_id, new_mapping_id)

    def test_add_protocol_to_identity_provider_bad_mapping(self):
        # Create an identity provider
        idp_id = data_utils.rand_uuid_hex()
        self.identity_providers_client.create_identity_provider(
            idp_id, **fixtures.idp_ref(enabled=True))

        # Now we try to add a protocol to the identity provider using
        # a non existent mapping ID
        mapping_id = data_utils.rand_uuid_hex()
        protocol_id = data_utils.rand_uuid_hex()
        protocol = self.identity_providers_client.add_protocol_and_mapping(
            idp_id, protocol_id, mapping_id)

        self._assert_protocol_attributes(protocol, protocol_id, mapping_id)

    def test_update_protocol_from_identity_provider_bad_mapping(self):
        idp_id, mapping_id = self._create_identity_provider_and_mapping()

        # Add a protocol to the identity provider
        protocol_id = data_utils.rand_uuid_hex()
        self.identity_providers_client.add_protocol_and_mapping(
            idp_id, protocol_id, mapping_id)

        # Update the identity provider protocol using a non existent
        # mapping_id
        new_mapping_id = data_utils.rand_uuid_hex()
        protocol = self.identity_providers_client.update_protocol_mapping(
            idp_id, protocol_id, new_mapping_id)

        self._assert_protocol_attributes(protocol, protocol_id, new_mapping_id)
