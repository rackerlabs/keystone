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

from six.moves import http_client

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

    def test_user_can_list_role_assignments(self):
        with self.test_client() as c:
            r = c.get('/v3/role_assignments', headers=self.headers)
            self.assertTrue(len(r.json['users']) == 1)

    def test_user_can_list_role_assignments_with_filter(self):
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?role.id=%s' %
                      self.bootstrapper.reader_role_id, headers=self.headers)
            self.assertTrue(len(r.json['users']) == 1)

    def test_user_can_list_role_assignments_with_multiple_filter(self):
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?role.id=%s&user.id=%s' %
                      (self.bootstrapper.reader_role_id,
                       self.system_reader_id),
                      headers=self.headers)
            self.assertTrue(len(r.json['users']) == 1)

    def test_user_can_list_role_assignments_with_include_names(self):
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?include_names=True',
                      headers=self.headers)
            self.assertTrue(len(r.json['users']) == 1)


class DomainReaderTests(base_classes.TestCaseWithBootstrap,
                        common_auth.AuthTestMixin):

    def setUp(self):
        super(DomainReaderTests, self).setUp()
        self.loadapp()
        self.useFixture(ksfixtures.Policy(self.config_fixture))
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        self.domain_id = domain['id']
        domain_reader = unit.new_user_ref(domain_id=self.domain_id)
        self.user_id = PROVIDERS.identity_api.create_user(domain_reader)['id']
        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.reader_role_id, user_id=self.user_id,
            domain_id=self.domain_id
        )

        auth = self.build_authentication_request(
            user_id=self.user_id, password=domain_reader['password'],
            domain_id=self.domain_id,
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}

    def test_user_can_list_role_assignments_in_their_domain(self):
        expected_user_ids = [self.user_id]
        for _ in range(3):
            user = PROVIDERS.identity_api.create_user(
                unit.new_user_ref(domain_id=self.domain_id)
            )
            expected_user_ids.append(user['id'])

        with self.test_client() as c:
            r = c.get('/v3/role_assignments',
                      headers=self.headers)
            self.assertTrue(len(r.json['users']) == 4)
            for user in r.json['users']:
                self.assertIn(user['id'], expected_user_ids)

    def test_user_cannot_list_role_assignments_in_other_domain(self):
        expected_user_ids = [self.user_id]
        for _ in range(3):
            user = PROVIDERS.identity_api.create_user(
                unit.new_user_ref(domain_id=self.domain_id)
            )
            expected_user_ids.append(user['id'])
        domain_id = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref())['id']
        with self.test_client() as c:
            c.get('/v3/role_assignments?domain_id=%s' % domain_id,
                  headers=self.headers,
                  expected_status_code=http_client.FORBIDDEN
                  )

    def test_user_can_list_role_assignments_with_filter_in_their_domain(self):
        expected_user_ids = [self.user_id]
        for _ in range(3):
            user = PROVIDERS.identity_api.create_user(
                unit.new_user_ref(domain_id=self.domain_id)
            )
            expected_user_ids.append(user['id'])
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?role.id=%s' %
                      self.bootstrapper.reader_role_id, headers=self.headers)
            self.assertTrue(len(r.json['users']) == 1)
            for user in r.json['users']:
                self.assertIn(user['id'], expected_user_ids)

    def test_user_list_assignments_with_include_names_in_their_domain(self):
        expected_user_ids = [self.user_id]
        for _ in range(3):
            user = PROVIDERS.identity_api.create_user(
                unit.new_user_ref(domain_id=self.domain_id)
            )
            expected_user_ids.append(user['id'])
        with self.test_client() as c:
            r = c.get('/v3/role_assignments?include_names=True',
                      headers=self.headers)
            self.assertTrue(len(r.json['users']) == 1)


class ProjectReaderTests(base_classes.TestCaseWithBootstrap,
                         common_auth.AuthTestMixin):
    def setUp(self):
        super(ProjectReaderTests, self).setUp()
        self.loadapp()
        self.useFixture(ksfixtures.Policy(self.config_fixture))
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        domain = PROVIDERS.resource_api.create_domain(
            uuid.uuid4().hex, unit.new_domain_ref()
        )
        self.domain_id = domain['id']

        project = unit.new_project_ref(domain_id=self.domain_id)
        project = PROVIDERS.resource_api.create_project(project['id'], project)
        self.project_id = project['id']

        project_reader = unit.new_user_ref(domain_id=self.domain_id)
        self.user_id = PROVIDERS.identity_api.create_user(project_reader)['id']
        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.reader_role_id, user_id=self.user_id,
            project_id=self.project_id
        )

        auth = self.build_authentication_request(
            user_id=self.user_id, password=project_reader['password'],
            project_id=self.project_id,
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}

    def test_user_cannot_list_role_assignments_in_their_domain(self):
        expected_user_ids = [self.user_id]
        for _ in range(3):
            user = PROVIDERS.identity_api.create_user(
                unit.new_user_ref(domain_id=self.domain_id)
            )
            expected_user_ids.append(user['id'])

        with self.test_client() as c:
            c.get('/v3/role_assignments',
                  headers=self.headers,
                  expected_status_code=http_client.FORBIDDEN)

    def test_user_cannot_list_role_assignments_in_other_domain(self):
        expected_user_ids = [self.user_id]
        for _ in range(3):
            user = PROVIDERS.identity_api.create_user(
                unit.new_user_ref(domain_id=self.domain_id)
            )
            expected_user_ids.append(user['id'])

        with self.test_client() as c:
            c.get('/v3/role_assignments', headers=self.headers,
                  expected_status_code=http_client.FORBIDDEN
                  )
