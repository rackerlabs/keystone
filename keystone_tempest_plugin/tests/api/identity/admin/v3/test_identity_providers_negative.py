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
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from tempest import test


class IndentityProvidersNegativeTestJSON(base.BaseIdentityV3AdminTest):

    @test.attr(type=['negative'])
    @test.idempotent_id('fb16231b-7bc6-4303-a51f-0fae2d759b07')
    def test_identity_provider_create_with_already_used_remote_id(self):
        # First, we create an identity provider with remote_ids
        idp_id1 = data_utils.rand_uuid_hex()
        remote_ids = ['remote_id1', 'remote_id2']
        self.identity_providers_client.create_identity_provider(
            idp_id1, enabled=True, remote_ids=remote_ids)['identity_provider']
        self.addCleanup(
            self.identity_providers_client.delete_identity_provider, idp_id1)

        # We can not create another identity provider reusing a remote_id
        idp_id2 = data_utils.rand_uuid_hex()
        remote_id = remote_ids[0]
        self.assertRaises(
            lib_exc.Conflict,
            self.identity_providers_client.create_identity_provider,
            idp_id2, enabled=True, remote_ids=[remote_id])

    @decorators.skip_because(bug='1558670')
    @test.attr(type=['negative'])
    @test.idempotent_id('98238a1b-7c9f-4b61-9ad1-ea208ba3baa8')
    def test_identity_provider_update_with_already_used_remote_id(self):
        # First, we create an identity provider with remote_ids
        idp_id1 = data_utils.rand_uuid_hex()
        remote_ids = ['remote_id1', 'remote_id2']
        self.identity_providers_client.create_identity_provider(
            idp_id1, enabled=True, remote_ids=remote_ids)['identity_provider']
        self.addCleanup(
            self.identity_providers_client.delete_identity_provider, idp_id1)

        # Create a second identity provider without remote_ids
        idp_id2 = data_utils.rand_uuid_hex()
        self.identity_providers_client.create_identity_provider(
            idp_id2, enabled=True)['identity_provider']
        self.addCleanup(
            self.identity_providers_client.delete_identity_provider, idp_id2)

        # We can not update idp2 reusing a remote_id from idp1
        remote_id = remote_ids[0]
        self.assertRaises(
            lib_exc.Conflict,
            self.identity_providers_client.update_identity_provider,
            idp_id2, enabled=True, remote_ids=[remote_id])

    @test.attr(type=['negative'])
    @test.idempotent_id('f7ae4a3d-b729-48ce-965f-e59b1259d49d')
    def test_identity_provider_get_not_found(self):
        # Try to get an identity provider using a random ID
        idp_id = data_utils.rand_uuid_hex()
        self.assertRaises(
            lib_exc.NotFound,
            self.identity_providers_client.show_identity_provider,
            idp_id)
