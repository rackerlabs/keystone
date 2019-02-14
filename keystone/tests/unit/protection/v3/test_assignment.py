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

<<<<<<< HEAD
    def _create_user_project_assignment(self):
        role = PROVIDERS.role_api.create_role(
            uuid.uuid4().hex, unit.new_role_ref()
        )
=======
    def _setup_test_role_assignments(self):
        # Utility to create assignments and return important data for
        # assertions.
>>>>>>> WIP: Additional work for testing assignment protection

        # Since the role doesn't really matter too much, we can just re-use an
        # existing role instead of creating a new one.
        role_id = self.bootstrapper.reader_role_id

        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        )

<<<<<<< HEAD
        PROVIDERS.assignment_api.add_role_to_user_and_project(
            user['id'], project['id'], role['id']
        )

        return user['id'], project['id']

    def _create_user_domain_assignment(self):
        role = PROVIDERS.role_api.create_role(
            uuid.uuid4().hex, unit.new_role_ref()
=======
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=CONF.identity.default_domain_id)
        )

        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
>>>>>>> WIP: Additional work for testing assignment protection
        )

        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )

<<<<<<< HEAD
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
=======
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
>>>>>>> WIP: Additional work for testing assignment protection
        )

        # create a group+project role assignment.
        PROVIDERS.assignment_api.create_grant(
            role_id, group_id=group['id'], project_id=project['id']
        )

<<<<<<< HEAD
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
=======
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

    def _extract_role_assignments_from_response_body(self, r):
        # Condense the role assignment details into a set of key things we can
        # use in assertions.
        assignments = []
        for assignment in r.json['role_assignments']:
            a = {}
            if 'project' in assignment['scope']:
                a['project_id'] = assignment['scope']['project']['id']
            elif 'domain' in assignment['scope']:
                a['domain_id'] = assignment['scope']['domain']['id']
            elif 'system' in assignment['scope']:
                a['system'] = 'all'

            if 'user' in assignment:
                a['user_id'] = assignment['user']['id']
            elif 'group' in assignment:
                a['group_id'] = assignment['group']['id']

            a['role_id'] = assignment['role']['id']

            assignments.append(a)
        return assignments

    def test_user_can_list_all_role_assignments_in_the_deployment(self):
        assignments = self._setup_test_role_assignments()
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
            r = c.get('/v3/role_assignments', headers=self.headers)
            self.assertEqual(len(expected), len(r.json['role_assignments']))
            actual = self._extract_role_assignments_from_response_body(r)
            for assignment in actual:
                self.assertIn(assignment, expected)

    def test_user_can_list_all_role_names_assignments_in_the_deployment(self):
        assignments = self._setup_test_role_assignments()
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
                '/v3/role_assignments?include_names=True', headers=self.headers
            )
            self.assertEqual(len(expected), len(r.json['role_assignments']))
            actual = self._extract_role_assignments_from_response_body(r)
            for assignment in actual:
                self.assertIn(assignment, expected)

    def test_user_can_filter_role_assignments_by_project(self):
        assignments = self._setup_test_role_assignments()
        expected = [
            {
                'user_id': assignments['user_id'],
                'project_id': assignments['project_id'],
                'role_id': assignments['role_id']
            },
            {
                'group_id': assignments['group_id'],
                'project_id': assignments['project_id'],
                'role_id': assignments['role_id']
            }
        ]
        project_id = assignments['project_id']

        with self.test_client() as c:
            r = c.get(
                '/v3/role_assignments?scope.project.id=%s' % project_id,
                headers=self.headers
            )
            self.assertEqual(len(expected), len(r.json['role_assignments']))
            actual = self._extract_role_assignments_from_response_body(r)
            for assignment in actual:
                self.assertIn(assignment, expected)

    def test_user_can_filter_role_assignments_by_domain(self):
        assignments = self._setup_test_role_assignments()
        expected = [
            {
                'user_id': assignments['user_id'],
                'domain_id': assignments['domain_id'],
                'role_id': assignments['role_id']
            },
            {
                'group_id': assignments['group_id'],
                'domain_id': assignments['domain_id'],
                'role_id': assignments['role_id']
            }
        ]
        domain_id = assignments['domain_id']

        with self.test_client() as c:
            r = c.get(
                '/v3/role_assignments?scope.domain.id=%s' % domain_id,
                headers=self.headers
            )
            self.assertEqual(len(expected), len(r.json['role_assignments']))
            actual = self._extract_role_assignments_from_response_body(r)
            for assignment in actual:
                self.assertIn(assignment, expected)

    def test_user_can_filter_role_assignments_by_system(self):
        assignments = self._setup_test_role_assignments()
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
                'system': 'all',
                'role_id': self.bootstrapper.admin_role_id
            },
            {
                'user_id': assignments['user_id'],
                'system': 'all',
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
                '/v3/role_assignments?scope.system=all',
                headers=self.headers
            )
            self.assertEqual(len(expected), len(r.json['role_assignments']))
            actual = self._extract_role_assignments_from_response_body(r)
            for assignment in actual:
                self.assertIn(assignment, expected)

    def test_user_can_filter_role_assignments_by_user(self):
        assignments = self._setup_test_role_assignments()
        expected = [
            # assignment of the user running the test case
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
            }
        ]
        user_id = assignments['user_id']

        with self.test_client() as c:
            r = c.get(
                '/v3/role_assignments?user.id=%s' % user_id,
                headers=self.headers
            )
            self.assertEqual(len(expected), len(r.json['role_assignments']))
            actual = self._extract_role_assignments_from_response_body(r)
            for assignment in actual:
                self.assertIn(assignment, expected)

    def test_user_can_filter_role_assignments_by_group(self):
        assignments = self._setup_test_role_assignments()
        expected = [
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
        group_id = assignments['group_id']

        with self.test_client() as c:
            r = c.get(
                '/v3/role_assignments?group.id=%s' % group_id,
                headers=self.headers
            )
            self.assertEqual(len(expected), len(r.json['role_assignments']))
            actual = self._extract_role_assignments_from_response_body(r)
            for assignment in actual:
                self.assertIn(assignment, expected)

    def test_user_can_filter_role_assignments_by_role(self):
        assignments = self._setup_test_role_assignments()
        expected = [
            # assignment of the user running the test case
            {
                'user_id': self.user_id,
                'system': 'all',
                'role_id': self.bootstrapper.reader_role_id
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
        role_id = assignments['role_id']

        with self.test_client() as c:
            r = c.get(
                '/v3/role_assignments?role.id=%s&include_names=True' % role_id,
                headers=self.headers
            )
            self.assertEqual(len(expected), len(r.json['role_assignments']))
            actual = self._extract_role_assignments_from_response_body(r)
            for assignment in actual:
                self.assertIn(assignment, expected)

    def test_user_can_filter_role_assignments_by_project_and_role(self):
        assignments = self._setup_test_role_assignments()
        expected = [
            {
                'user_id': assignments['user_id'],
                'project_id': assignments['project_id'],
                'role_id': assignments['role_id']
            },
            {
                'group_id': assignments['group_id'],
                'project_id': assignments['project_id'],
                'role_id': assignments['role_id']
            },
        ]

        with self.test_client() as c:
            qs = (assignments['project_id'], assignments['role_id'])
            r = c.get(
                '/v3/role_assignments?scope.project.id=%s&role.id=%s' % qs,
                headers=self.headers
            )
            self.assertEqual(len(expected), len(r.json['role_assignments']))
            actual = self._extract_role_assignments_from_response_body(r)
            for assignment in actual:
                self.assertIn(assignment, expected)

    def test_user_can_filter_role_assignments_by_domain_and_role(self):
        assignments = self._setup_test_role_assignments()
        expected = [
            {
                'user_id': assignments['user_id'],
                'domain_id': assignments['domain_id'],
                'role_id': assignments['role_id']
            },
            {
                'group_id': assignments['group_id'],
                'domain_id': assignments['domain_id'],
                'role_id': assignments['role_id']
            },
        ]
        qs = (assignments['domain_id'], assignments['role_id'])

        with self.test_client() as c:
            r = c.get(
                '/v3/role_assignments?scope.domain.id=%s&role.id=%s' % qs,
                headers=self.headers
            )
            self.assertEqual(len(expected), len(r.json['role_assignments']))
            actual = self._extract_role_assignments_from_response_body(r)
            for assignment in actual:
                self.assertIn(assignment, expected)
        pass

    def test_user_can_filter_role_assignments_by_system_and_role(self):
        assignments = self._setup_test_role_assignments()
        expected = [
            # assignment of the user running the test case
            {
                'user_id': self.user_id,
                'system': 'all',
                'role_id': self.bootstrapper.reader_role_id
            },
            {
                'user_id': assignments['user_id'],
                'system': 'all',
                'role_id': assignments['role_id']
            },
            {
                'group_id': assignments['group_id'],
                'system': 'all',
                'role_id': assignments['role_id']
            }
        ]
        role_id = assignments['role_id']

        with self.test_client() as c:
            r = c.get(
                '/v3/role_assignments?scope.system=all&role.id=%s' % role_id,
                headers=self.headers
            )
            self.assertEqual(len(expected), len(r.json['role_assignments']))
            actual = self._extract_role_assignments_from_response_body(r)
            for assignment in actual:
                self.assertIn(assignment, expected)

    def test_user_can_filter_role_assignments_by_user_and_role(self):
        assignments = self._setup_test_role_assignments()
        expected = [
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
            }
        ]
        qs = (assignments['user_id'], assignments['role_id'])

        with self.test_client() as c:
            r = c.get(
                '/v3/role_assignments?user.id=%s&role.id=%s' % qs,
                headers=self.headers
            )
            self.assertEqual(len(expected), len(r.json['role_assignments']))
            actual = self._extract_role_assignments_from_response_body(r)
            for assignment in actual:
                self.assertIn(assignment, expected)
        pass

    def test_user_can_filter_role_assignments_by_group_and_role(self):
        assignments = self._setup_test_role_assignments()
        expected = [
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
            qs = (assignments['group_id'], assignments['role_id'])
            r = c.get(
                '/v3/role_assignments?group.id=%s&role.id=%s' % qs,
                headers=self.headers
            )
            self.assertEqual(len(expected), len(r.json['role_assignments']))
            actual = self._extract_role_assignments_from_response_body(r)
            for assignment in actual:
                self.assertIn(assignment, expected)
>>>>>>> WIP: Additional work for testing assignment protection
