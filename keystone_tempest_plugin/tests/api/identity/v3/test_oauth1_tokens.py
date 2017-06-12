# Copyright 2017 AT&T Corporation.
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

from tempest.lib.common.utils import data_utils
from tempest.lib.common.utils import test_utils
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from keystone_tempest_plugin.tests import base


class OAUTH1TokensTest(base.BaseIdentityTest):

    def _create_consumer(self):
        """Creates a consumer with a random description."""
        description = data_utils.rand_name('test_create_consumer')
        consumer = self.oauth_consumers_client.create_consumer(
            description)['consumer']
        # cleans up created consumers after tests
        self.addCleanup(test_utils.call_and_ignore_notfound_exc,
                        self.oauth_consumers_client.delete_consumer,
                        consumer['id'])
        return consumer

    def _create_request_token(self, consumer):
        """Create request token"""
        project_id = self.oauth_token_client \
                         .auth_provider.credentials.project_id

        request_token = self.oauth_token_client.create_request_token(
            consumer['id'], consumer['secret'], project_id)
        return request_token

    def _authorize_request_token(self, request_token):
        """Authorize request token"""
        user_id = self.oauth_token_client \
                      .auth_provider.credentials.user_id
        project_id = self.oauth_token_client \
                         .auth_provider.credentials.project_id
        roles = self.roles_client.list_user_roles_on_project(
            project_id, user_id)
        role_ids = [role['id'] for role in roles['roles']]

        oauth_verifier = self.oauth_token_client.authorize_request_token(
            request_token['oauth_token'], role_ids)
        return oauth_verifier['token']

    def _create_access_token(self, consumer):
        """Create access token"""
        request_token = self._create_request_token(consumer)
        oauth_verifier = self._authorize_request_token(request_token)

        access_token = self.oauth_token_client.create_access_token(
            consumer['id'], consumer['secret'],
            request_token['oauth_token'],
            request_token['oauth_token_secret'],
            oauth_verifier['oauth_verifier'])

        # cleans up access tokens after tests
        user_id = self.oauth_token_client.auth_provider.credentials.user_id
        self.addCleanup(test_utils.call_and_ignore_notfound_exc,
                        self.oauth_token_client.revoke_access_token,
                        user_id, access_token['oauth_token'])
        return access_token

    @decorators.idempotent_id('c8307ea6-a86c-47fd-ae7b-5b3b2caca76d')
    def test_create_and_show_consumer(self):
        """Tests to make sure that a consumer with parameters is made"""
        consumer = self._create_consumer()
        # fetch created consumer from client
        fetched_consumer = self.oauth_consumers_client.show_consumer(
            consumer['id'])['consumer']
        # assert that the fetched consumer matches the created one and
        # has all parameters
        for key in ['description', 'id', 'links']:
            self.assertEqual(consumer[key], fetched_consumer[key])

    @decorators.idempotent_id('fdfa1b7f-2a31-4354-b2c7-f6ae20554f93')
    def test_delete_consumer(self):
        """Tests the delete function."""
        consumer = self._create_consumer()
        # fetch consumer from client to confirm it exists
        fetched_consumer = self.oauth_consumers_client.show_consumer(
            consumer['id'])['consumer']
        self.assertEqual(consumer['id'], fetched_consumer['id'])
        # delete existing consumer
        self.oauth_consumers_client.delete_consumer(consumer['id'])
        # check that consumer no longer exists
        self.assertRaises(lib_exc.NotFound,
                          self.oauth_consumers_client.show_consumer,
                          consumer['id'])

    @decorators.idempotent_id('080a9b1a-c009-47c0-9979-5305bf72e3dc')
    def test_update_consumer(self):
        """Tests the update functionality"""
        # create a new consumer to update
        consumer = self._create_consumer()
        # create new description
        new_description = data_utils.rand_name('test_update_consumer')
        # update consumer
        self.oauth_consumers_client.update_consumer(consumer['id'],
                                                    new_description)
        # check that the same consumer now has the new description
        updated_consumer = self.oauth_consumers_client.show_consumer(
            consumer['id'])['consumer']
        self.assertEqual(new_description, updated_consumer['description'])

    @decorators.idempotent_id('09ca50de-78f2-4ffb-ac71-f2254036b2b8')
    def test_list_consumers(self):
        """Test for listing consumers"""
        # create two consumers to populate list
        new_consumer_one = self._create_consumer()
        new_consumer_two = self._create_consumer()
        # fetch the list of consumers
        consumer_list = self.oauth_consumers_client \
                            .list_consumers()['consumers']
        # add fetched consumer ids to a list
        id_list = [consumer['id'] for consumer in consumer_list]
        # check if created consumers are in the list
        self.assertIn(new_consumer_one['id'], id_list)
        self.assertIn(new_consumer_two['id'], id_list)

    @decorators.idempotent_id('40f6644e-95b4-49d8-98b2-0573c50c20c1')
    def test_create_request_token(self):
        """Test to create request token"""
        consumer = self._create_consumer()
        request_token = self._create_request_token(consumer)
        # check that oauth token id and secret exists
        self.assertIsNotNone(request_token['oauth_token'])
        self.assertIsNotNone(request_token['oauth_token_secret'])

    @decorators.idempotent_id('2c85ff29-6745-4482-bdfa-02d9a3430836')
    def test_authorize_request_token(self):
        """Test to authorize a request token"""
        consumer = self._create_consumer()
        request_token = self._create_request_token(consumer)
        oauth_verifier = self._authorize_request_token(request_token)
        # check that oauth verifier exists
        self.assertIsNotNone(oauth_verifier['oauth_verifier'])

    @decorators.idempotent_id('225f6ca9-3871-4dd9-b54c-d0e416ec5457')
    def test_create_access_token(self):
        """Test to create access token"""
        consumer = self._create_consumer()
        access_token = self._create_access_token(consumer)

        user_id = self.oauth_token_client.auth_provider.credentials.user_id
        project_id = self.oauth_token_client \
                         .auth_provider.credentials.project_id
        fetched_access_token = self.oauth_token_client.get_access_token(
            user_id, access_token['oauth_token'])['access_token']
        # check that access token details matches
        self.assertEqual(access_token['oauth_token'],
                         fetched_access_token['id'])
        self.assertEqual(consumer['id'], fetched_access_token['consumer_id'])
        self.assertEqual(access_token['oauth_expires_at'],
                         fetched_access_token['expires_at'])
        self.assertEqual(project_id, fetched_access_token['project_id'])
        self.assertEqual(user_id, fetched_access_token['authorizing_user_id'])

    @decorators.idempotent_id('a25e77dd-9e16-478c-aba6-0a774f08ad6a')
    def test_revoke_access_token(self):
        """Test to delete the access token"""
        consumer = self._create_consumer()
        access_token = self._create_access_token(consumer)

        user_id = self.oauth_token_client.auth_provider.credentials.user_id
        # delete existing access token
        self.oauth_token_client.revoke_access_token(
            user_id, access_token['oauth_token'])
        # check that access token no longer exist
        self.assertRaises(lib_exc.NotFound,
                          self.oauth_token_client.get_access_token,
                          user_id,
                          access_token['oauth_token'])

    @decorators.idempotent_id('e8f72994-fbe3-4be9-bb67-236a06c6f0d0')
    def test_list_access_tokens(self):
        """Test to list access tokens"""
        # create two consumers and access token for each
        new_consumer_one = self._create_consumer()
        new_consumer_two = self._create_consumer()
        access_token_one = self._create_access_token(new_consumer_one)
        access_token_two = self._create_access_token(new_consumer_two)

        user_id = self.oauth_token_client.auth_provider.credentials.user_id
        # fetch the list of access tokens
        access_token_list = self.oauth_token_client \
                                .list_access_tokens(user_id)['access_tokens']
        # add fetch access token ids to a list
        id_list = [access_token['id'] for access_token in access_token_list]
        # check if created access tokens are in the list
        self.assertIn(access_token_one['oauth_token'], id_list)
        self.assertIn(access_token_two['oauth_token'], id_list)

    @decorators.idempotent_id('b606d964-0e21-4981-a72f-2fcbcfba9559')
    def test_list_roles_for_access_token(self):
        """Test to list roles for an access token"""
        consumer = self._create_consumer()
        access_token = self._create_access_token(consumer)

        user_id = self.oauth_token_client.auth_provider.credentials.user_id
        project_id = self.oauth_token_client \
                         .auth_provider.credentials.project_id
        fetched_roles = self.oauth_token_client.list_access_token_roles(
            user_id, access_token['oauth_token'])['roles']
        fetched_role_ids = [role['id'] for role in fetched_roles]
        roles = self.roles_client.list_user_roles_on_project(
            project_id, user_id)
        role_ids = [role['id'] for role in roles['roles']]

        # check that role ids matches
        self.assertItemsEqual(fetched_role_ids, role_ids)

    @decorators.idempotent_id('fb561bef-fafa-4714-b4e8-620785324161')
    def test_show_role_for_access_token(self):
        """Test to show role details for an access token"""
        consumer = self._create_consumer()
        access_token = self._create_access_token(consumer)

        user_id = self.oauth_token_client.auth_provider.credentials.user_id
        project_id = self.oauth_token_client \
                         .auth_provider.credentials.project_id
        roles = self.roles_client.list_user_roles_on_project(
            project_id, user_id)
        fetched_role = self.oauth_token_client.get_access_token_role(
            user_id,
            access_token['oauth_token'],
            roles['roles'][0]['id'])

        # check that role id matches
        self.assertEqual(fetched_role['role']['id'], roles['roles'][0]['id'])
