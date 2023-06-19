#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import http.client
import uuid

from oslo_serialization import jsonutils

from keystone.common.policies import group as gp
from keystone.common import provider_api
import keystone.conf
from keystone.tests.common import auth as common_auth
from keystone.tests import unit
from keystone.tests.unit import base_classes
from keystone.tests.unit import ksfixtures
from keystone.tests.unit.ksfixtures import temporaryfile

CONF = keystone.conf.CONF
PROVIDERS = provider_api.ProviderAPIs


class _SystemUserGroupTests:
    """Common default functionality for all system users."""

    def test_user_can_list_groups(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )

        with self.test_client() as c:
            r = c.get('/v3/groups', headers=self.headers)
            self.assertEqual(1, len(r.json['groups']))
            self.assertEqual(group['id'], r.json['groups'][0]['id'])

    def test_user_can_get_a_group(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )

        with self.test_client() as c:
            r = c.get(
                '/v3/groups/{}'.format(group['id']), headers=self.headers
            )
            self.assertEqual(group['id'], r.json['group']['id'])

    def test_user_can_list_group_members(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=domain['id'])
        )

        PROVIDERS.identity_api.add_user_to_group(user['id'], group['id'])

        with self.test_client() as c:
            r = c.get(
                '/v3/groups/{}/users'.format(group['id']), headers=self.headers
            )
            self.assertEqual(1, len(r.json['users']))
            self.assertEqual(user['id'], r.json['users'][0]['id'])

    def test_user_can_list_groups_for_other_users(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=domain['id'])
        )

        PROVIDERS.identity_api.add_user_to_group(user['id'], group['id'])

        with self.test_client() as c:
            r = c.get(
                '/v3/users/{}/groups'.format(user['id']), headers=self.headers
            )
            self.assertEqual(1, len(r.json['groups']))
            self.assertEqual(group['id'], r.json['groups'][0]['id'])

    def test_user_can_check_if_user_in_group(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=domain['id'])
        )

        PROVIDERS.identity_api.add_user_to_group(user['id'], group['id'])

        with self.test_client() as c:
            c.get(
                '/v3/groups/{}/users/{}'.format(group['id'], user['id']),
                headers=self.headers,
                expected_status_code=http.client.NO_CONTENT,
            )

    def test_user_cannot_get_non_existent_group_not_found(self):
        with self.test_client() as c:
            c.get(
                f'/v3/groups/{uuid.uuid4().hex}',
                headers=self.headers,
                expected_status_code=http.client.NOT_FOUND,
            )


class _SystemAndDomainMemberAndReaderGroupTests:
    """Common default functionality for system readers and system members."""

    expected_status_for_create = http.client.FORBIDDEN
    expected_status_for_update = http.client.FORBIDDEN
    expected_status_for_delete = http.client.FORBIDDEN
    expected_status_for_add_user_to_group = http.client.FORBIDDEN
    expected_status_for_remove_user_from_group = http.client.FORBIDDEN

    def test_user_cannot_create_group(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )

        create = {
            'group': {'name': uuid.uuid4().hex, 'domain_id': domain['id']}
        }

        with self.test_client() as c:
            c.post(
                '/v3/groups',
                json=create,
                headers=self.headers,
                expected_status_code=self.expected_status_for_create,
            )

    def test_user_cannot_update_group(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )

        update = {'group': {'description': uuid.uuid4().hex}}

        with self.test_client() as c:
            c.patch(
                '/v3/groups/{}'.format(group['id']),
                json=update,
                headers=self.headers,
                expected_status_code=self.expected_status_for_update,
            )

    def test_user_cannot_delete_group(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )

        with self.test_client() as c:
            c.delete(
                '/v3/groups/{}'.format(group['id']),
                headers=self.headers,
                expected_status_code=self.expected_status_for_delete,
            )

    def test_user_cannot_add_users_to_group(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=domain['id'])
        )

        with self.test_client() as c:
            c.put(
                '/v3/groups/{}/users/{}'.format(group['id'], user['id']),
                headers=self.headers,
                expected_status_code=self.expected_status_for_add_user_to_group,
            )

    def test_user_cannot_remove_users_from_group(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=domain['id'])
        )

        PROVIDERS.identity_api.add_user_to_group(user['id'], group['id'])

        with self.test_client() as c:
            c.delete(
                '/v3/groups/{}/users/{}'.format(group['id'], user['id']),
                headers=self.headers,
                expected_status_code=self.expected_status_for_remove_user_from_group,
            )


class SystemReaderTests(
    base_classes.TestCaseWithBootstrap,
    common_auth.AuthTestMixin,
    _SystemUserGroupTests,
    _SystemAndDomainMemberAndReaderGroupTests,
):
    def setUp(self):
        super().setUp()
        self.loadapp()
        self.useFixture(ksfixtures.Policy(self.config_fixture))
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        system_reader = unit.new_user_ref(
            domain_id=CONF.identity.default_domain_id
        )
        self.user_id = PROVIDERS.identity_api.create_user(system_reader)['id']
        PROVIDERS.assignment_api.create_system_grant_for_user(
            self.user_id, self.bootstrapper.reader_role_id
        )

        auth = self.build_authentication_request(
            user_id=self.user_id,
            password=system_reader['password'],
            system=True,
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}


class SystemMemberTests(
    base_classes.TestCaseWithBootstrap,
    common_auth.AuthTestMixin,
    _SystemUserGroupTests,
    _SystemAndDomainMemberAndReaderGroupTests,
):
    def setUp(self):
        super().setUp()
        self.loadapp()
        self.useFixture(ksfixtures.Policy(self.config_fixture))
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        system_member = unit.new_user_ref(
            domain_id=CONF.identity.default_domain_id
        )
        self.user_id = PROVIDERS.identity_api.create_user(system_member)['id']
        PROVIDERS.assignment_api.create_system_grant_for_user(
            self.user_id, self.bootstrapper.member_role_id
        )

        auth = self.build_authentication_request(
            user_id=self.user_id,
            password=system_member['password'],
            system=True,
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}


class SystemAdminTests(
    base_classes.TestCaseWithBootstrap,
    common_auth.AuthTestMixin,
    _SystemUserGroupTests,
):
    def setUp(self):
        super().setUp()
        self.loadapp()
        self.useFixture(ksfixtures.Policy(self.config_fixture))
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        self.user_id = self.bootstrapper.admin_user_id
        auth = self.build_authentication_request(
            user_id=self.user_id,
            password=self.bootstrapper.admin_password,
            system=True,
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}

    def test_user_can_create_group(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )

        create = {
            'group': {'name': uuid.uuid4().hex, 'domain_id': domain['id']}
        }

        with self.test_client() as c:
            c.post('/v3/groups', json=create, headers=self.headers)

    def test_user_can_update_group(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )

        update = {'group': {'description': uuid.uuid4().hex}}

        with self.test_client() as c:
            c.patch(
                '/v3/groups/{}'.format(group['id']),
                json=update,
                headers=self.headers,
            )

    def test_user_can_delete_group(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )

        with self.test_client() as c:
            c.delete('/v3/groups/{}'.format(group['id']), headers=self.headers)

    def test_user_can_add_users_to_group(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=domain['id'])
        )

        with self.test_client() as c:
            c.put(
                '/v3/groups/{}/users/{}'.format(group['id'], user['id']),
                headers=self.headers,
            )

    def test_user_can_remove_users_from_group(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=domain['id'])
        )

        PROVIDERS.identity_api.add_user_to_group(user['id'], group['id'])

        with self.test_client() as c:
            c.delete(
                '/v3/groups/{}/users/{}'.format(group['id'], user['id']),
                headers=self.headers,
            )


class _DomainUserGroupTests:
    expected_status_for_get_group_in_other_domain: int = http.client.FORBIDDEN
    expected_status_for_get_group_nonexistent: int = http.client.FORBIDDEN
    expected_status_for_list_groups_for_user_in_other_domain: int = (
        http.client.FORBIDDEN
    )
    expected_status_for_list_groups_for_user_nonexistent: int = (
        http.client.FORBIDDEN
    )
    expected_status_for_list_users_in_group_other_domain: int = (
        http.client.FORBIDDEN
    )
    expected_status_for_list_users_in_group_nonexistent: int = (
        http.client.FORBIDDEN
    )
    expected_status_for_check_user_in_group_other_domain: int = (
        http.client.FORBIDDEN
    )

    def test_user_can_list_groups_in_domain(self):
        # second domain
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        # one group in new domain
        group1 = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )
        # one group in user's domain
        group2 = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=self.domain_id)
        )

        # user should only see one group
        with self.test_client() as c:
            r = c.get('/v3/groups', headers=self.headers)
            self.assertEqual(1, len(r.json['groups']))
            self.assertNotIn(group1['id'], [g['id'] for g in r.json['groups']])
            self.assertEqual(group2['id'], r.json['groups'][0]['id'])

    def test_user_cannot_list_groups_in_other_domain(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )
        with self.test_client() as c:
            r = c.get(
                '/v3/groups?domain_id={}'.format(domain['id']),
                headers=self.headers,
            )
            self.assertEqual(0, len(r.json['groups']))

    def test_user_can_get_group_in_domain(self):
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=self.domain_id)
        )
        with self.test_client() as c:
            r = c.get(
                '/v3/groups/{}'.format(group['id']), headers=self.headers
            )
            self.assertEqual(group['id'], r.json['group']['id'])

    def test_user_cannot_get_group_in_other_domain(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )
        with self.test_client() as c:
            c.get(
                '/v3/groups/{}'.format(group['id']),
                headers=self.headers,
                expected_status_code=self.expected_status_for_get_group_in_other_domain,
            )

    def test_user_cannot_get_non_existent_group_forbidden(self):
        with self.test_client() as c:
            c.get(
                f'/v3/groups/{uuid.uuid4().hex}',
                headers=self.headers,
                expected_status_code=self.expected_status_for_get_group_nonexistent,
            )

    def test_user_can_list_groups_in_domain_for_user_in_domain(self):
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=self.domain_id)
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=self.domain_id)
        )
        PROVIDERS.identity_api.add_user_to_group(user['id'], group['id'])
        with self.test_client() as c:
            r = c.get(
                '/v3/users/{}/groups'.format(user['id']), headers=self.headers
            )
            self.assertEqual(1, len(r.json['groups']))
            self.assertEqual(group['id'], r.json['groups'][0]['id'])

    def test_user_cannot_list_groups_in_own_domain_user_in_other_domain(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=domain['id'])
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=self.domain_id)
        )
        PROVIDERS.identity_api.add_user_to_group(user['id'], group['id'])
        with self.test_client() as c:
            c.get(
                '/v3/users/{}/groups'.format(user['id']),
                headers=self.headers,
                expected_status_code=self.expected_status_for_list_groups_for_user_in_other_domain,
            )

    def test_user_cannot_list_groups_for_non_existent_user_forbidden(self):
        with self.test_client() as c:
            c.get(
                f'/v3/users/{uuid.uuid4().hex}/groups',
                headers=self.headers,
                expected_status_code=self.expected_status_for_list_groups_for_user_nonexistent,
            )

    def test_user_cannot_list_groups_in_other_domain_user_in_own_domain(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=self.domain_id)
        )
        # one group in other domain
        group1 = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )
        # one group in own domain
        group2 = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=self.domain_id)
        )
        PROVIDERS.identity_api.add_user_to_group(user['id'], group1['id'])
        PROVIDERS.identity_api.add_user_to_group(user['id'], group2['id'])
        with self.test_client() as c:
            r = c.get(
                '/v3/users/{}/groups'.format(user['id']), headers=self.headers
            )
            # only one group should be visible
            self.assertEqual(1, len(r.json['groups']))
            self.assertEqual(group2['id'], r.json['groups'][0]['id'])

    def test_user_can_list_users_in_own_domain_for_group_in_own_domain(self):
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=self.domain_id)
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=self.domain_id)
        )
        PROVIDERS.identity_api.add_user_to_group(user['id'], group['id'])
        with self.test_client() as c:
            r = c.get(
                '/v3/groups/{}/users'.format(group['id']), headers=self.headers
            )
            self.assertEqual(1, len(r.json['users']))
            self.assertEqual(user['id'], r.json['users'][0]['id'])

    def test_user_cannot_list_users_in_other_domain_group_in_own_domain(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        # one user in other domain
        user1 = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=domain['id'])
        )
        # one user in own domain
        user2 = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=self.domain_id)
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=self.domain_id)
        )
        PROVIDERS.identity_api.add_user_to_group(user1['id'], group['id'])
        PROVIDERS.identity_api.add_user_to_group(user2['id'], group['id'])
        with self.test_client() as c:
            r = c.get(
                '/v3/groups/{}/users'.format(group['id']), headers=self.headers
            )
            # only one user should be visible
            self.assertEqual(1, len(r.json['users']))
            self.assertEqual(user2['id'], r.json['users'][0]['id'])

    def test_user_cannot_list_users_in_own_domain_group_in_other_domain(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=self.domain_id)
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )
        PROVIDERS.identity_api.add_user_to_group(user['id'], group['id'])
        with self.test_client() as c:
            c.get(
                '/v3/groups/{}/users'.format(group['id']),
                headers=self.headers,
                expected_status_code=self.expected_status_for_list_users_in_group_other_domain,
            )

    def test_user_cannot_list_users_in_non_existent_group_forbidden(self):
        with self.test_client() as c:
            c.get(
                f'/v3/groups/{uuid.uuid4().hex}/users',
                headers=self.headers,
                expected_status_code=self.expected_status_for_list_users_in_group_nonexistent,
            )

    def test_user_can_check_user_in_own_domain_group_in_own_domain(self):
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=self.domain_id)
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=self.domain_id)
        )
        PROVIDERS.identity_api.add_user_to_group(user['id'], group['id'])
        with self.test_client() as c:
            c.head(
                '/v3/groups/{group}/users/{user}'.format(
                    group=group['id'], user=user['id']
                ),
                headers=self.headers,
                expected_status_code=http.client.NO_CONTENT,
            )
            c.get(
                '/v3/groups/{group}/users/{user}'.format(
                    group=group['id'], user=user['id']
                ),
                headers=self.headers,
                expected_status_code=http.client.NO_CONTENT,
            )

    def test_user_cannot_check_user_in_other_domain_group_in_own_domain(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=domain['id'])
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=self.domain_id)
        )
        PROVIDERS.identity_api.add_user_to_group(user['id'], group['id'])
        with self.test_client() as c:
            c.head(
                '/v3/groups/{group}/users/{user}'.format(
                    group=group['id'], user=user['id']
                ),
                headers=self.headers,
                expected_status_code=self.expected_status_for_check_user_in_group_other_domain,
            )
            c.get(
                '/v3/groups/{group}/users/{user}'.format(
                    group=group['id'], user=user['id']
                ),
                headers=self.headers,
                expected_status_code=self.expected_status_for_check_user_in_group_other_domain,
            )


class DomainReaderTests(
    base_classes.TestCaseWithBootstrap,
    common_auth.AuthTestMixin,
    _DomainUserGroupTests,
    _SystemAndDomainMemberAndReaderGroupTests,
):
    def setUp(self):
        super().setUp()
        self.loadapp()
        self.policy_file = self.useFixture(temporaryfile.SecureTempFile())
        self.policy_file_name = self.policy_file.file_name
        self.useFixture(
            ksfixtures.Policy(
                self.config_fixture, policy_file=self.policy_file_name
            )
        )
        self._override_policy()
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        self.domain_id = domain['id']
        domain_admin = unit.new_user_ref(domain_id=self.domain_id)
        self.user_id = PROVIDERS.identity_api.create_user(domain_admin)['id']
        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.reader_role_id,
            user_id=self.user_id,
            domain_id=self.domain_id,
        )

        auth = self.build_authentication_request(
            user_id=self.user_id,
            password=domain_admin['password'],
            domain_id=self.domain_id,
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}

    def _override_policy(self):
        with open(self.policy_file_name, 'w') as f:
            overridden_policies = {
                'identity:get_group': gp.ADMIN_OR_SYSTEM_READER_OR_DOMAIN_READER,
                'identity:list_groups': gp.ADMIN_OR_SYSTEM_READER_OR_DOMAIN_READER,
                'identity:list_groups_for_user': gp.ADMIN_OR_SYSTEM_READER_OR_DOMAIN_READER_FOR_TARGET_OR_OWNER,
                'identity:list_users_in_group': gp.ADMIN_OR_SYSTEM_READER_OR_DOMAIN_READER,
                'identity:check_user_in_group': gp.ADMIN_OR_SYSTEM_READER_OR_DOMAIN_READER_FOR_TARGET_GROUP,
            }
            f.write(jsonutils.dumps(overridden_policies))


class DomainMemberTests(
    base_classes.TestCaseWithBootstrap,
    common_auth.AuthTestMixin,
    _DomainUserGroupTests,
    _SystemAndDomainMemberAndReaderGroupTests,
):
    def setUp(self):
        super().setUp()
        self.loadapp()
        self.policy_file = self.useFixture(temporaryfile.SecureTempFile())
        self.policy_file_name = self.policy_file.file_name
        self.useFixture(
            ksfixtures.Policy(
                self.config_fixture, policy_file=self.policy_file_name
            )
        )
        self._override_policy()
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        self.domain_id = domain['id']
        domain_admin = unit.new_user_ref(domain_id=self.domain_id)
        self.user_id = PROVIDERS.identity_api.create_user(domain_admin)['id']
        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.member_role_id,
            user_id=self.user_id,
            domain_id=self.domain_id,
        )

        auth = self.build_authentication_request(
            user_id=self.user_id,
            password=domain_admin['password'],
            domain_id=self.domain_id,
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}

    def _override_policy(self):
        with open(self.policy_file_name, 'w') as f:
            overridden_policies = {
                'identity:get_group': gp.ADMIN_OR_SYSTEM_READER_OR_DOMAIN_READER,
                'identity:list_groups': gp.ADMIN_OR_SYSTEM_READER_OR_DOMAIN_READER,
                'identity:list_groups_for_user': gp.ADMIN_OR_SYSTEM_READER_OR_DOMAIN_READER_FOR_TARGET_OR_OWNER,
                'identity:list_users_in_group': gp.ADMIN_OR_SYSTEM_READER_OR_DOMAIN_READER,
                'identity:check_user_in_group': gp.ADMIN_OR_SYSTEM_READER_OR_DOMAIN_READER_FOR_TARGET_GROUP,
            }
            f.write(jsonutils.dumps(overridden_policies))


class DomainAdminTests(
    base_classes.TestCaseWithBootstrap,
    common_auth.AuthTestMixin,
    _DomainUserGroupTests,
):
    expected_status_for_get_group_in_other_domain = http.client.OK
    expected_status_for_get_group_nonexistent = http.client.NOT_FOUND
    expected_status_for_list_groups_for_user_in_other_domain = http.client.OK
    expected_status_for_list_groups_for_user_nonexistent = (
        http.client.NOT_FOUND
    )
    expected_status_for_list_users_in_group_other_domain = http.client.OK
    expected_status_for_list_users_in_group_nonexistent = http.client.NOT_FOUND
    expected_status_for_check_user_in_group_other_domain = (
        http.client.NO_CONTENT
    )

    def setUp(self):
        super().setUp()
        self.loadapp()
        self.policy_file = self.useFixture(temporaryfile.SecureTempFile())
        self.policy_file_name = self.policy_file.file_name
        self.useFixture(
            ksfixtures.Policy(
                self.config_fixture, policy_file=self.policy_file_name
            )
        )
        self._override_policy()
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        self.domain_id = domain['id']
        domain_admin = unit.new_user_ref(domain_id=self.domain_id)
        self.user_id = PROVIDERS.identity_api.create_user(domain_admin)['id']
        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.admin_role_id,
            user_id=self.user_id,
            domain_id=self.domain_id,
        )

        auth = self.build_authentication_request(
            user_id=self.user_id,
            password=domain_admin['password'],
            domain_id=self.domain_id,
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}

    def _override_policy(self):
        with open(self.policy_file_name, 'w') as f:
            overridden_policies = {
                'identity:get_group': gp.ADMIN_OR_SYSTEM_READER_OR_DOMAIN_READER,
                'identity:list_groups': gp.ADMIN_OR_SYSTEM_READER_OR_DOMAIN_READER,
                'identity:list_groups_for_user': gp.ADMIN_OR_SYSTEM_READER_OR_DOMAIN_READER_FOR_TARGET_OR_OWNER,
                'identity:create_group': gp.ADMIN_OR_DOMAIN_MANAGER_FOR_GROUPS,
                'identity:update_group': gp.ADMIN_OR_DOMAIN_MANAGER_FOR_GROUPS,
                'identity:delete_group': gp.ADMIN_OR_DOMAIN_MANAGER_FOR_GROUPS,
                'identity:list_users_in_group': gp.ADMIN_OR_SYSTEM_READER_OR_DOMAIN_READER,
                'identity:remove_user_from_group': gp.ADMIN_OR_DOMAIN_MANAGER_FOR_GROUP_ASSIGNMENTS,
                'identity:check_user_in_group': gp.ADMIN_OR_SYSTEM_READER_OR_DOMAIN_READER_FOR_TARGET_GROUP,
                'identity:add_user_to_group': gp.ADMIN_OR_DOMAIN_MANAGER_FOR_GROUP_ASSIGNMENTS,
            }
            f.write(jsonutils.dumps(overridden_policies))

    def test_user_can_create_group_for_own_domain(self):
        create = {
            'group': {'name': uuid.uuid4().hex, 'domain_id': self.domain_id}
        }

        with self.test_client() as c:
            c.post('/v3/groups', json=create, headers=self.headers)

    def test_user_cannot_create_group_for_other_domain(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )

        create = {
            'group': {'name': uuid.uuid4().hex, 'domain_id': domain['id']}
        }

        with self.test_client() as c:
            c.post(
                '/v3/groups',
                json=create,
                headers=self.headers,
                expected_status_code=http.client.CREATED,
            )

    def test_user_can_update_group_in_own_domain(self):
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=self.domain_id)
        )

        update = {'group': {'description': uuid.uuid4().hex}}
        with self.test_client() as c:
            c.patch(
                '/v3/groups/{}'.format(group['id']),
                json=update,
                headers=self.headers,
            )

    def test_user_cannot_update_group_in_other_domain(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )

        update = {'group': {'description': uuid.uuid4().hex}}
        with self.test_client() as c:
            c.patch(
                '/v3/groups/{}'.format(group['id']),
                json=update,
                headers=self.headers,
                expected_status_code=http.client.OK,
            )

    def test_user_can_delete_group_in_own_domain(self):
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=self.domain_id)
        )
        with self.test_client() as c:
            c.delete('/v3/groups/{}'.format(group['id']), headers=self.headers)

    def test_user_cannot_delete_group_in_other_domain(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )
        with self.test_client() as c:
            c.delete(
                '/v3/groups/{}'.format(group['id']),
                headers=self.headers,
                expected_status_code=http.client.NO_CONTENT,
            )

    def test_user_can_remove_user_in_own_domain_from_group_in_own_domain(self):
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=self.domain_id)
        )
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=self.domain_id)
        )
        PROVIDERS.identity_api.add_user_to_group(user['id'], group['id'])
        with self.test_client() as c:
            c.delete(
                '/v3/groups/{group}/users/{user}'.format(
                    group=group['id'], user=user['id']
                ),
                headers=self.headers,
            )

    def test_user_cannot_remove_user_other_domain_from_group_own_domain(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=self.domain_id)
        )
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=domain['id'])
        )
        PROVIDERS.identity_api.add_user_to_group(user['id'], group['id'])
        with self.test_client() as c:
            c.delete(
                '/v3/groups/{group}/users/{user}'.format(
                    group=group['id'], user=user['id']
                ),
                headers=self.headers,
                expected_status_code=http.client.NO_CONTENT,
            )

    def test_user_cannot_remove_user_own_domain_from_group_other_domain(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=self.domain_id)
        )
        PROVIDERS.identity_api.add_user_to_group(user['id'], group['id'])
        with self.test_client() as c:
            c.delete(
                '/v3/groups/{group}/users/{user}'.format(
                    group=group['id'], user=user['id']
                ),
                headers=self.headers,
                expected_status_code=http.client.NO_CONTENT,
            )

    def test_user_cannot_remove_non_existent_user_from_group_forbidden(self):
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=self.domain_id)
        )
        with self.test_client() as c:
            c.delete(
                '/v3/groups/{group}/users/{user}'.format(
                    group=group['id'], user=uuid.uuid4().hex
                ),
                headers=self.headers,
                expected_status_code=http.client.NOT_FOUND,
            )

    def test_user_cannot_remove_user_from_non_existent_group_forbidden(self):
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=self.domain_id)
        )
        with self.test_client() as c:
            c.delete(
                '/v3/groups/{group}/users/{user}'.format(
                    group=uuid.uuid4().hex, user=user['id']
                ),
                headers=self.headers,
                expected_status_code=http.client.NOT_FOUND,
            )

    def test_user_can_add_user_in_own_domain_to_group_in_own_domain(self):
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=self.domain_id)
        )
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=self.domain_id)
        )
        with self.test_client() as c:
            c.put(
                '/v3/groups/{group}/users/{user}'.format(
                    group=group['id'], user=user['id']
                ),
                headers=self.headers,
            )

    def test_user_cannot_add_user_other_domain_to_group_own_domain(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=self.domain_id)
        )
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=domain['id'])
        )
        with self.test_client() as c:
            c.put(
                '/v3/groups/{group}/users/{user}'.format(
                    group=group['id'], user=user['id']
                ),
                headers=self.headers,
                expected_status_code=http.client.NO_CONTENT,
            )

    def test_user_cannot_add_user_own_domain_to_group_other_domain(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=self.domain_id)
        )
        with self.test_client() as c:
            c.put(
                '/v3/groups/{group}/users/{user}'.format(
                    group=group['id'], user=user['id']
                ),
                headers=self.headers,
                expected_status_code=http.client.NO_CONTENT,
            )

    def test_user_cannot_add_non_existent_user_to_group_forbidden(self):
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=self.domain_id)
        )
        with self.test_client() as c:
            c.put(
                '/v3/groups/{group}/users/{user}'.format(
                    group=group['id'], user=uuid.uuid4().hex
                ),
                headers=self.headers,
                expected_status_code=http.client.NOT_FOUND,
            )

    def test_user_cannot_add_user_from_non_existent_group_forbidden(self):
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=self.domain_id)
        )
        with self.test_client() as c:
            c.put(
                '/v3/groups/{group}/users/{user}'.format(
                    group=uuid.uuid4().hex, user=user['id']
                ),
                headers=self.headers,
                expected_status_code=http.client.NOT_FOUND,
            )


class ProjectUserTests(
    base_classes.TestCaseWithBootstrap, common_auth.AuthTestMixin
):
    def setUp(self):
        super().setUp()
        self.loadapp()
        self.useFixture(ksfixtures.Policy(self.config_fixture))
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        self.domain_id = domain['id']

        user = unit.new_user_ref(domain_id=self.domain_id)
        self.user_id = PROVIDERS.identity_api.create_user(user)['id']

        project = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex, unit.new_project_ref(domain_id=self.domain_id)
        )
        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.member_role_id,
            user_id=self.user_id,
            project_id=project['id'],
        )

        auth = self.build_authentication_request(
            user_id=self.user_id,
            password=user['password'],
            project_id=project['id'],
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}

    def test_user_can_get_list_their_own_groups(self):
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=self.domain_id)
        )

        PROVIDERS.identity_api.add_user_to_group(self.user_id, group['id'])

        with self.test_client() as c:
            r = c.get(f'/v3/users/{self.user_id}/groups', headers=self.headers)
            self.assertEqual(1, len(r.json['groups']))
            self.assertEqual(group['id'], r.json['groups'][0]['id'])

    def test_user_cannot_list_groups_for_other_users(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=domain['id'])
        )

        PROVIDERS.identity_api.add_user_to_group(user['id'], group['id'])

        with self.test_client() as c:
            c.get(
                '/v3/users/{}/groups'.format(user['id']),
                headers=self.headers,
                expected_status_code=http.client.FORBIDDEN,
            )

    def test_user_cannot_list_groups(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )

        with self.test_client() as c:
            c.get(
                '/v3/groups',
                headers=self.headers,
                expected_status_code=http.client.FORBIDDEN,
            )

    def test_user_cannot_get_a_group(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )

        with self.test_client() as c:
            c.get(
                '/v3/groups/{}'.format(group['id']),
                headers=self.headers,
                expected_status_code=http.client.FORBIDDEN,
            )

    def test_user_cannot_list_group_members(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=domain['id'])
        )

        PROVIDERS.identity_api.add_user_to_group(user['id'], group['id'])

        with self.test_client() as c:
            c.get(
                '/v3/groups/{}/users'.format(group['id']),
                headers=self.headers,
                expected_status_code=http.client.FORBIDDEN,
            )

    def test_user_cannot_check_if_user_in_group(self):
        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=domain['id'])
        )

        PROVIDERS.identity_api.add_user_to_group(user['id'], group['id'])

        with self.test_client() as c:
            c.get(
                '/v3/groups/{}/users/{}'.format(group['id'], user['id']),
                headers=self.headers,
                expected_status_code=http.client.FORBIDDEN,
            )

    def test_user_cannot_get_non_existent_group_forbidden(self):
        with self.test_client() as c:
            c.get(
                f'/v3/groups/{uuid.uuid4().hex}',
                headers=self.headers,
                expected_status_code=http.client.FORBIDDEN,
            )
