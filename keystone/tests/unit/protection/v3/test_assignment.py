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
        self.system_reader_id = PROVIDERS.identity_api.create_user(
            system_reader
        )['id']
        PROVIDERS.assignment_api.create_system_grant_for_user(
            self.system_reader_id, self.bootstrapper.reader_role_id
        )

        auth = self.build_authentication_request(
            user_id=self.system_reader_id, password=system_reader['password'],
            system=True
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}

    def test_user_can_list_all_role_assignments_on_system(self):
        role = PROVIDERS.role_api.create_role(uuid.uuid4().hex,
                                              unit.new_role_ref())

        project = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id))

        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        )

        PROVIDERS.assignment_api.add_role_to_user_and_project(
            role_id=role['id'], user_id=user['id'], tenant_id=project['id'])
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.system=all', headers=self.headers)
            print(len(r.json['role_assignments']))
            self.assertTrue(len(r.json['role_assignments']) == 2)

    def test_user_specific_list_role_assignments_on_system(self):
        role = PROVIDERS.role_api.create_role(uuid.uuid4().hex,
                                              unit.new_role_ref())

        project = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id))

        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        )

        PROVIDERS.assignment_api.add_role_to_user_and_project(
            role_id=role['id'], user_id=user['id'], tenant_id=project['id'])
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.system=all?user.id=%s',
                      user,
                      headers=self.headers)
            print(len(r.json['role_assignments']))
            self.assertTrue(len(r.json['role_assignments']) == 4)

    def test_user_can_list_role_assignments_with_filter(self):
        role = PROVIDERS.role_api.create_role(uuid.uuid4().hex,
                                              unit.new_role_ref())

        project = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id))

        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        )

        PROVIDERS.assignment_api.add_role_to_user_and_project(
            role_id=role['id'], user_id=user['id'], tenant_id=project['id'])
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.system=all?project.id=%s' %
                      project,
                      headers=self.headers)
            self.assertTrue(r.json['role_assignments'][0]['scope']['project']
                            ['id'], project['id'])

    def test_user_can_list_role_assignments_with_multiple_filter(self):
        role = PROVIDERS.role_api.create_role(uuid.uuid4().hex,
                                              unit.new_role_ref())

        project = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id))

        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        )

        PROVIDERS.assignment_api.add_role_to_user_and_project(
            role_id=role['id'], user_id=user['id'], tenant_id=project['id'])
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.system=all?'
                      'project.id=%s?user.id=%s' % (project, user),
                      headers=self.headers)
            self.assertTrue(r.json['role_assignments'][0]['scope']['project']
                            ['id'], project['id'])
            self.assertTrue(r.json['role_assignments'][2]['user']
                            ['id'], user['id'])

    def test_user_can_list_role_assignments_with_include_names(self):
        role = PROVIDERS.role_api.create_role(uuid.uuid4().hex,
                                              unit.new_role_ref())

        project = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id))

        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        )

        PROVIDERS.assignment_api.add_role_to_user_and_project(
            role_id=role['id'], user_id=user['id'], tenant_id=project['id'])
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.system=all?'
                      'include_names=True', headers=self.headers)
            print(len(r.json['role_assignments']))
            self.assertTrue(len(r.json['role_assignments']) == 4)

    def test_user_can_list_role_assignments_within_domain(self):
        role = PROVIDERS.role_api.create_role(uuid.uuid4().hex,
                                              unit.new_role_ref())

        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        )

        PROVIDERS.assignment_api.create_grant(
            role_id=role['id'], user_id=user['id'],
            domain_id=CONF.identity.default_domain_id)
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.system=all?domain.id=%s',
                      CONF.identity.default_domain_id,
                      headers=self.headers)
            self.assertTrue(r.json['role_assignments'][1]['scope']['domain']
                            ['id'], CONF.identity.default_domain_id)

    def test_user_can_list_role_assignments_another_domain(self):
        role = PROVIDERS.role_api.create_role(uuid.uuid4().hex,
                                              unit.new_role_ref())

        project = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id))

        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        )

        PROVIDERS.assignment_api.add_role_to_user_and_project(
            role_id=role['id'], user_id=user['id'], tenant_id=project['id'])
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.system=all?project.id=%s' %
                      project,
                      headers=self.headers)
            self.assertTrue(r.json['role_assignments'][0]['scope']['project']
                            ['id'], project['id'])

    def test_user_can_list_role_assignments_another_project(self):
        role = PROVIDERS.role_api.create_role(uuid.uuid4().hex,
                                              unit.new_role_ref())

        project1 = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id))

        project2 = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id))

        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        )

        PROVIDERS.assignment_api.add_role_to_user_and_project(
            role_id=role['id'], user_id=user['id'], tenant_id=project1['id'])
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.system=all?project.id=%s' %
                      project2,
                      headers=self.headers)
            self.assertTrue(r.json['role_assignments'][0]['scope']['project']
                            ['id'], project2['id'])

    def test_user_in_another_group_can_list_role_assignments(self):
        role = PROVIDERS.role_api.create_role(uuid.uuid4().hex,
                                              unit.new_role_ref())

        project = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id))

        group1 = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=CONF.identity.default_domain_id))

        group2 = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=CONF.identity.default_domain_id))

        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        )

        PROVIDERS.identity_api.add_user_to_group(
            user_id=user['id'], group_id=group1['id'])

        # Assign a role to the group on a project
        PROVIDERS.assignment_api.create_grant(
            role_id=role['id'], group_id=group2['id'], project_id=project['id'])

        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.system=all?group.id=%s?'
                      'user.id=%s' % (group1, user), headers=self.headers)
            self.assertTrue(r.json['role_assignments'][0]['scope']['project']
                            ['id'], project['id'])

    def test_group_can_list_role_assignments_with_filter(self):
        role = PROVIDERS.role_api.create_role(uuid.uuid4().hex,
                                              unit.new_role_ref())

        project = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id))

        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=CONF.identity.default_domain_id))

        PROVIDERS.assignment_api.create_grant(
            role_id=role['id'], group_id=group['id'], project_id=project['id'])
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.system=all?project.id=%s?'
                      'group.id=%s' % (project, group),
                      headers=self.headers)
            self.assertTrue(r.json['role_assignments'][0]['scope']['project']
                            ['id'], project['id'])

    def test_group_can_list_role_assignments_another_project(self):
        role = PROVIDERS.role_api.create_role(uuid.uuid4().hex,
                                              unit.new_role_ref())

        project1 = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id))

        project2 = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id))

        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=CONF.identity.default_domain_id))

        PROVIDERS.assignment_api.create_grant(
            role_id=role['id'], group_id=group['id'], project_id=project1['id'])
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.system=all?project.id=%s?'
                      'group.id=%s' % (project2, group), headers=self.headers)
            self.assertTrue(r.json['role_assignments'][0]['scope']['project']
                            ['id'], project2['id'])

    def test_group_can_list_role_assignments_within_domain(self):
        role = PROVIDERS.role_api.create_role(uuid.uuid4().hex,
                                              unit.new_role_ref())
        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=CONF.identity.default_domain_id))

        PROVIDERS.assignment_api.create_grant(
            role_id=role['id'], user_id=group['id'],
            domain_id=CONF.identity.default_domain_id)

        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.system=all?group.id=%s',
                      group, headers=self.headers)
            self.assertTrue(r.json['role_assignments'][1]['scope']['domain']
                            ['id'], CONF.identity.default_domain_id)

    def test_group_can_list_role_assignments_another_domain(self):
        role = PROVIDERS.role_api.create_role(uuid.uuid4().hex,
                                              unit.new_role_ref())
        domainD = unit.new_domain_ref()
        domain = PROVIDERS.resource_api.create_domain(domainD['id'], domainD)

        group = PROVIDERS.identity_api.create_group(
            unit.new_group_ref(domain_id=CONF.identity.default_domain_id))

        PROVIDERS.assignment_api.create_grant(
            role_id=role['id'], user_id=group['id'],
            domain_id=CONF.identity.default_domain_id)

        with self.test_client() as c:
            r = c.get('/v3/role_assignments?scope.system=all?domain.id=%s?'
                      'group.id=%s' % (domain, group), headers=self.headers)
            self.assertTrue(r.json['role_assignments'][1]['scope']['domain']
                            ['id'], domain)
