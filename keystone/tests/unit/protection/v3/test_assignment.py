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

    def _setup_test_role_assignments(self):
        # Utility to create assignments and return important data for
        # assertions.

        # since the role doesn't really matter too much, we can just re-use an
        # existing role instead of creating a new one.
        role_id = self.bootstrapper.reader_role_id

        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        )

        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=CONF.identity.default_domain_id)
        )

        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )

        project = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id)
        )

        # create a user+project role assignment.
        PROVIDERS.assignment_api.create_grant(
            role_id, user_id=user['id'], project_id=project['id']
        )

        # create a user+domain role assignment.
        PROVIDERS.assignment_api.create_grant(
            role_id, user_id=user['id'], domain_id=domain['id']
        )

        # create a user+system role assignment.
        PROVIDERS.assignment_api.create_system_grant_for_user(
            user['id'], role_id
        )

        # create a group+project role assignment.
        PROVIDERS.assignment_api.create_grant(
            role_id, group_id=group['id'], project_id=project['id']
        )

        # create a group+domain role assignment.
        PROVIDERS.assignment_api.create_grant(
            role_id, group_id=group['id'], domain_id=domain['id']
        )

        # create a group+system role assignment.
        PROVIDERS.assignment_api.create_system_grant_for_group(
            group['id'], role_id
        )

        return {
            'user_id': user['id'],
            'group_id': group['id'],
            'domain_id': domain['id'],
            'project_id': project['id'],
            'role_id': role_id,
        }

    def test_user_can_list_all_role_assignments(self):
        assignments = self._setup_test_role_assignments()

        # list all assignments and make sure every assignment created and all
        # assignments from bootstrap exist.
        expected = [
            # assignment of the user running the test case
            {
                'user_id': self.user_id,
                'system': 'all',
                'role_id': self.bootstrapper.reader_role_id
            },
            # this assignment is created by keystone-manage bootstrap
            {
                'user_id': self.bootstrapper.admin_user_id,
                'project_id': self.bootstrapper.project_id,
                'role_id': self.bootstrapper.admin_role_id
            },
            # this assignment is created by keystone-manage bootstrap
            {
                'user_id': self.bootstrapper.admin_user_id,
                'system': 'all',
                'role_id': self.bootstrapper.admin_role_id
            },
            {
                'user_id': assignments['user_id'],
                'project_id': assignments['project_id'],
                'role_id': assignments['role_id']
            },
            {
                'user_id': assignments['user_id'],
                'domain_id': assignments['domain_id'],
                'role_id': assignments['role_id']
            },
            {
                'user_id': assignments['user_id'],
                'system': 'all',
                'role_id': assignments['role_id']
            },
            {
                'group_id': assignments['group_id'],
                'project_id': assignments['project_id'],
                'role_id': assignments['role_id']
            },
            {
                'group_id': assignments['group_id'],
                'domain_id': assignments['domain_id'],
                'role_id': assignments['role_id']
            },
            {
                'group_id': assignments['group_id'],
                'system': 'all',
                'role_id': assignments['role_id']
            }
        ]

        with self.test_client() as c:
            r = c.get(
                '/v3/role_assignments?include_names=True',
                headers=self.headers
            )
            # we could improve this assertion by checking all the assignments
            # returned are the assignments we actually expect.
            self.assertEqual(len(expected), len(r.json['role_assignments']))

    def test_user_can_filter_role_assignments_by_project(self):
        self._setup_test_role_assignments()
        # grant the user additional roles on other projects.
        # list assignments and make sure only the assignments for the project
        # in question are returned.
        pass

    def test_user_can_filter_role_assignments_by_domain(self):
        self._setup_test_role_assignments()
        # create the user additional roles on other domains.
        # make sure only assignments for the domain in question are returned,
        # and don't include the users other assignments on projects, other
        # domains, or the system.
        pass

    def test_user_can_filter_role_assignments_by_system(self):
        self._setup_test_role_assignments()
        # make sure only the user's system role assignments are returned,
        # excluding the user's project or domain assignments.
        pass

    def test_user_can_filter_role_assignments_by_user(self):
        self._setup_test_role_assignments()
        # ensure the user has assignments on projects, domains, and the system.
        # make sure the assignments returned are only for that user.
        pass

    def test_user_can_filter_role_assignments_by_group(self):
        self._setup_test_role_assignments()
        # ensure the group has assignments on projects, domains, and the
        # system.
        # make sure the assignments returned are only for that group.
        pass

    def test_user_can_filter_role_assignments_by_role(self):
        self._setup_test_role_assignments()
        # reuse the same role for multiple assignments.
        # make sure the assignments returned are only for that role.
        pass

    def test_user_can_list_all_role_assignments_on_system(self):
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
            self.user_id, project['id'], role['id']
        )

        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.system=all', headers=self.headers)
            self.assertTrue(len(r.json['role_assignments']) == 2)
            for assignment in r.json['role_assignments']:
                self.assertNotEqual(user, assignment['user']['id'])

    def test_user_can_list_role_assignments_by_project(self):
        role = PROVIDERS.role_api.create_role(
            uuid.uuid4().hex, unit.new_role_ref()
        )

        project = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id)
        )

        PROVIDERS.assignment_api.add_role_to_user_and_project(
            self.user_id, project['id'], role['id']
        )
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.project.id=%s' %
                      project['id'],
                      headers=self.headers)
            self.assertTrue(len(r.json['role_assignments']) == 1)
            for assignment in r.json['role_assignments']:
                self.assertEqual(self.user_id, assignment['user']['id'])

    def test_user_can_list_role_assignments_by_project_and_role(self):
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
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.project.id=%s&role.id=%s'
                      % (project['id'], role['id']),
                      headers=self.headers)
            self.assertTrue(len(r.json['role_assignments']) == 1)
            for assignment in r.json['role_assignments']:
                self.assertEqual(user['id'], assignment['user']['id'])

    def test_user_can_list_role_assignments_with_include_names(self):
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
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?include_names=True?user.id=%s'
                      % self.user_id, headers=self.headers)
            self.assertTrue(len(r.json['role_assignments']) == 4)

    def test_user_can_list_role_assignments_within_domain(self):
        role = PROVIDERS.role_api.create_role(
            uuid.uuid4().hex, unit.new_role_ref()
        )

        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        )

        PROVIDERS.assignment_api.create_grant(
            role['id'], user_id=user['id'],
            domain_id=CONF.identity.default_domain_id
        )
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.domain.id=%s'
                      % CONF.identity.default_domain_id, headers=self.headers)
            self.assertTrue(len(r.json['role_assignments']) == 1)
            for assignment in r.json['role_assignments']:
                self.assertEqual(user['id'], assignment['user']['id'])

    def test_user_can_list_role_assignments_another_domain(self):
        role = PROVIDERS.role_api.create_role(
            uuid.uuid4().hex, unit.new_role_ref()
        )

        domainD = unit.new_domain_ref()
        domain = PROVIDERS.resource_api.create_domain(
            domainD['id'], domainD
        )

        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=domain['id'])
        )

        PROVIDERS.assignment_api.create_grant(
            role['id'], user_id=user['id'],
            domain_id=domain['id']
        )
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.domain.id=%s'
                      % domain['id'], headers=self.headers)
            self.assertTrue(len(r.json['role_assignments']) == 1)
            for assignment in r.json['role_assignments']:
                self.assertEqual(user['id'], assignment['user']['id'])

    def test_user_can_list_role_assignments_another_project(self):
        role = PROVIDERS.role_api.create_role(
            uuid.uuid4().hex, unit.new_role_ref()
        )

        project1 = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id)
        )

        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        )

        PROVIDERS.assignment_api.add_role_to_user_and_project(
            user['id'], project1['id'], role['id']
        )
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.project.id=%s' %
                      project1['id'],
                      headers=self.headers)
            self.assertTrue(len(r.json['role_assignments']) == 1)
            for assignment in r.json['role_assignments']:
                self.assertEqual(user['id'], assignment['user']['id'])

    def test_user_can_list_group_role_assignments(self):
        role = PROVIDERS.role_api.create_role(
            uuid.uuid4().hex, unit.new_role_ref()
        )

        project = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id)
        )

        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=CONF.identity.default_domain_id))

        PROVIDERS.identity_api.add_user_to_group(
            user_id=self.user_id, group_id=group['id']
        )

        # Assign a role to the group on a project
        PROVIDERS.assignment_api.create_grant(
            role_id=role['id'], group_id=group['id'], project_id=project['id']
        )
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?group.id=%s'
                      % group['id'], headers=self.headers)
            self.assertTrue(len(r.json['role_assignments']) == 1)
            for assignment in r.json['role_assignments']:
                self.assertEqual(group['id'], assignment['group']['id'])

    def test_user_can_list_group_role_assignments_within_project(self):
        role = PROVIDERS.role_api.create_role(
            uuid.uuid4().hex, unit.new_role_ref()
        )

        project = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id)
        )

        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=CONF.identity.default_domain_id)
        )

        PROVIDERS.identity_api.add_user_to_group(
            user_id=self.user_id, group_id=group['id']
        )

        PROVIDERS.assignment_api.create_grant(
            role_id=role['id'], group_id=group['id'], project_id=project['id']
        )
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.project.id=%s'
                      % project['id'],
                      headers=self.headers)
            self.assertTrue(len(r.json['role_assignments']) == 1)
            for assignment in r.json['role_assignments']:
                self.assertEqual(group['id'], assignment['group']['id'])

    def test_user_can_list_group_role_assignments_within_domain(self):
        role = PROVIDERS.role_api.create_role(
            uuid.uuid4().hex, unit.new_role_ref()
        )
        domainD = unit.new_domain_ref()
        domain = PROVIDERS.resource_api.create_domain(domainD['id'], domainD)

        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=domain['id'])
        )

        PROVIDERS.identity_api.add_user_to_group(
            user_id=self.user_id, group_id=group['id']
        )

        PROVIDERS.assignment_api.create_grant(
            role_id=role['id'], group_id=group['id'],
            domain_id=domain['id']
        )

        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.domain.id=%s'
                      % domain['id'],
                      headers=self.headers)
            self.assertTrue(len(r.json['role_assignments']) == 1)
            for assignment in r.json['role_assignments']:
                self.assertEqual(group['id'], assignment['group']['id'])
