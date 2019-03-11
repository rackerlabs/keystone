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


class _AssignmentTestUtilities(object):
    """Useful utilities for setting up test assignments and assertions."""

    def _setup_test_role_assignments(self):
        # Utility to create assignments and return important data for
        # assertions.

        # Since the role doesn't really matter too much, we can just re-use an
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


class SystemReaderTests(base_classes.TestCaseWithBootstrap,
                        common_auth.AuthTestMixin,
                        _AssignmentTestUtilities):

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
        self.expected = [
            # assignment of the user running the test case
            {
                'user_id': self.user_id,
                'system': 'all',
                'role_id': self.bootstrapper.reader_role_id
            }
        ]
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

    def test_check_user_grant_on_system(self):
        assignments = self._setup_test_role_assignments()
        with self.test_client() as c:
            c.head('/v3/system/users/%s/roles/%s'
                   % (assignments['user_id'], self.bootstrapper.reader_role_id),
                   headers=self.headers,
                   expected_status_code=http_client.NO_CONTENT)

    def test_check_user_grant_on_domain(self):
        assignments = self._setup_test_role_assignments()
        with self.test_client() as c:
            c.head('/v3/domains/%s/users/%s/roles/%s'
                   % (assignments['domain_id'], assignments['user_id'],
                      self.bootstrapper.reader_role_id),
                   headers=self.headers,
                   expected_status_code=http_client.NO_CONTENT)

    def test_check_user_grant_on_project(self):
        assignments = self._setup_test_role_assignments()
        with self.test_client() as c:
            c.head('/v3/projects/%s/users/%s/roles/%s'
                   % (assignments['project_id'], assignments['user_id'],
                      self.bootstrapper.reader_role_id),
                   headers=self.headers,
                   expected_status_code=http_client.NO_CONTENT)

    def test_check_group_grant_on_system(self):
        assignments = self._setup_test_role_assignments()
        with self.test_client() as c:
            c.head('/v3/system/groups/%s/roles/%s'
                   % (assignments['group_id'],
                      self.bootstrapper.reader_role_id),
                   headers=self.headers,
                   expected_status_code=http_client.NO_CONTENT)

    def test_check_group_grant_on_domain(self):
        assignments = self._setup_test_role_assignments()
        with self.test_client() as c:
            c.head('/v3/domains/%s/groups/%s/roles/%s'
                   % (assignments['domain_id'], assignments['group_id'],
                      self.bootstrapper.reader_role_id),
                   headers=self.headers,
                   expected_status_code=http_client.NO_CONTENT)

    def test_check_group_grant_on_project(self):
        assignments = self._setup_test_role_assignments()
        with self.test_client() as c:
            c.head('/v3/projects/%s/groups/%s/roles/%s'
                   % (assignments['project_id'], assignments['group_id'],
                      self.bootstrapper.reader_role_id),
                   headers=self.headers,
                   expected_status_code=http_client.NO_CONTENT)

    def test_list_grants_of_user_on_system(self):
        assignments = self._setup_test_role_assignments()
        print(assignments)
        with self.test_client() as c:
            r = c.get('/v3/system/users/%s/roles' % (assignments['user_id']),
                      headers=self.headers)

    def test_list_grants_of_user_on_domain(self):
        assignments = self._setup_test_role_assignments()
        with self.test_client() as c:
            r = c.get('/v3/domains/%s/users/%s/roles'
                      % (assignments['domain_id'], assignments['user_id']),
                      headers=self.headers)

    def test_list_grants_of_user_on_project(self):
        assignments = self._setup_test_role_assignments()
        with self.test_client() as c:
            r = c.get('/v3/projects/%s/users/%s/roles'
                      % (assignments['project_id'], assignments['user_id']),
                      headers=self.headers)

    def test_list_grants_of_group_on_system(self):
        assignments = self._setup_test_role_assignments()
        print(assignments)
        with self.test_client() as c:
            r = c.get('/v3/system/groups/%s/roles' % (assignments['group_id']),
                      headers=self.headers)

    def test_list_grants_of_group_on_domain(self):
        assignments = self._setup_test_role_assignments()
        with self.test_client() as c:
            r = c.get('/v3/domains/%s/groups/%s/roles'
                      % (assignments['domain_id'], assignments['group_id']),
                      headers=self.headers)

    def test_list_grants_of_group_on_project(self):
        assignments = self._setup_test_role_assignments()
        with self.test_client() as c:
            r = c.get('/v3/projects/%s/groups/%s/roles'
                      % (assignments['project_id'], assignments['group_id']),
                      headers=self.headers)
