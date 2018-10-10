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

import uuid

from keystone.common import provider_api
import keystone.conf
from keystone.tests.common import auth as common_auth
from keystone.tests import unit
from keystone.tests.unit import base_classes
from keystone.tests.unit import ksfixtures

CONF = keystone.conf.CONF
PROVIDERS = provider_api.ProviderAPIs


class SystemReaderTests(base_classes.TestCaseWithBootstrap,
                        common_auth.AuthTestMixin):

    def setUp(self):
        super(SystemReaderTests, self).setUp()
        self.loadapp()
        self.useFixture(ksfixtures.Policy(self.config_fixture))
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        system_reader = unit.new_user_ref(
            domain_id=CONF.identity.default_domain_id
        )
        self.user_id = PROVIDERS.identity_api.create_user(
            system_reader
        )['id']
        PROVIDERS.assignment_api.create_system_grant_for_user(
            self.user_id, self.bootstrapper.reader_role_id
        )

        auth = self.build_authentication_request(
            user_id=self.user_id, password=system_reader['password'],
            system=True
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}

    def _create_user_project_assignment(self):
        role = PROVIDERS.role_api.create_role(
            uuid.uuid4().hex, unit.new_role_ref()
        )

        project = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id)
        )

        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        )

        PROVIDERS.assignment_api.add_role_to_user_and_project(
            user['id'], project['id'], role['id']
        )

        return user['id'], project['id']

    def _create_user_domain_assignment(self):
        role = PROVIDERS.role_api.create_role(
            uuid.uuid4().hex, unit.new_role_ref()
        )

        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )

        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=domain['id'])
        )

        PROVIDERS.assignment_api.create_grant(
            role['id'], user_id=user['id'],
            domain_id=domain['id']
        )

        return user['id'], domain['id']

    def _create_user_system_assignment(self):
        role = PROVIDERS.role_api.create_role(
            uuid.uuid4().hex, unit.new_role_ref()
        )

        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )

        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=domain['id'])
        )

        PROVIDERS.assignment_api.create_system_grant_for_user(
            user['id'], role['id']
        )

        return user['id']

    def _create_group_project_assignment(self):
        role = PROVIDERS.role_api.create_role(
            uuid.uuid4().hex, unit.new_role_ref()
        )

        project = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id)
        )

        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=CONF.identity.default_domain_id))

        PROVIDERS.assignment_api.create_grant(
            role['id'], group_id=group['id'], project_id=project['id']
        )

        return group['id'], project['id']

    def _create_group_domain_assignment(self):
        role = PROVIDERS.role_api.create_role(
            uuid.uuid4().hex, unit.new_role_ref()
        )

        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )

        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id']))

        PROVIDERS.assignment_api.create_grant(
            role['id'], group_id=group['id'], domain_id=domain['id']
        )

        return group['id'], domain['id']

    def _create_group_system_assignment(self):
        role = PROVIDERS.role_api.create_role(
            uuid.uuid4().hex, unit.new_role_ref()
        )

        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )

        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id']))

        PROVIDERS.assignment_api.create_system_grant_for_group(
            group['id'], role['id']
        )

        return group['id']

    def test_user_can_list_all_assignments(self):
        self._create_user_project_assignment()
        self._create_user_domain_assignment()
        self._create_user_system_assignment()
        self._create_group_project_assignment()
        self._create_group_domain_assignment()
        self._create_group_system_assignment()

        with self.test_client() as c:
            r = c.get('/v3/role_assignments', headers=self.headers)
            # This assertion could be better, but just showing an example of
            # bootstrapping all possible permutations of various assignments
            # and that a system-reader can user a system-scoped token to get
            # all of them. All tests beyond this point should ensure that we
            # filter responses appropriately.
            self.assertEqual(9, len(r.json['role_assignments']))

    def test_user_can_filter_assignments_by_system(self):
        user_id, project_id = self._create_user_project_assignment()
        with self.test_client() as c:
            r = c.get(
                '/v3/role_assignments?scope.system=all', headers=self.headers
            )
            self.assertTrue(len(r.json['role_assignments']) == 2)
            expected_system = {'system': {'all': True}}
            for assignment in r.json['role_assignments']:
                self.assertNotEqual(user_id, assignment['user']['id'])
                self.assertEqual(expected_system, assignment['scope'])

    def test_user_can_filter_assignments_by_project(self):
        user_id, project_id = self._create_user_project_assignment()
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.project.id=%s' % project_id,
                      headers=self.headers)
            self.assertTrue(r.json['role_assignments'][0]['scope']['project']
                            ['id'], project_id)
            for assignment in r.json['role_assignments']:
                self.assertEqual(user_id, assignment['user']['id'])

    def test_user_can_filter_assignments_by_project_and_user(self):
        user_id, project_id = self._create_user_project_assignment()
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.project.id=%s?user.id=%s'
                      % (project_id, user_id),
                      headers=self.headers)
            for assignment in r.json['role_assignments']:
                self.assertEqual(
                    project_id, assignment['scope']['project']['id']
                )
                self.assertEqual(user_id, assignment['user']['id'])

    def test_user_can_list_role_assignments_by_domain(self):
        user_id, domain_id = self._create_user_domain_assignment()
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.domain.id=%s' % domain_id,
                      headers=self.headers)
            self.assertTrue(len(r.json['role_assignments']) == 1)
            for assignment in r.json['role_assignments']:
                self.assertEqual(user_id, assignment['user']['id'])
                self.assertEqual(
                    domain_id, assignment['scope']['domain']['id']
                )

    def test_user_can_filter_assignments_by_group(self):
        group_id, project_id = self._create_group_project_assignment()
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?group.id=%s'
                      % group_id, headers=self.headers)
            self.assertTrue(len(r.json['role_assignments']) == 1)
            for assignment in r.json['role_assignments']:
                self.assertEqual(group_id, assignment['group']['id'])

    def test_user_can_list_group_role_assignments_within_project(self):
        group_id, project_id = self._create_group_project_assignment()
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.project.id=%s'
                      % project_id,
                      headers=self.headers)
            self.assertTrue(len(r.json['role_assignments']) == 1)
            for assignment in r.json['role_assignments']:
                self.assertEqual(group_id, assignment['group']['id'])

    def test_user_can_list_group_role_assignments_within_domain(self):
        group_id, domain_id = self._create_group_domain_assignment()
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.domain.id=%s'
                      % domain_id,
                      headers=self.headers)
            self.assertTrue(len(r.json['role_assignments']) == 1)
            for assignment in r.json['role_assignments']:
                self.assertEqual(group_id, assignment['group']['id'])
