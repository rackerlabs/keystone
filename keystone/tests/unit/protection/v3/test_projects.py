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


class _CommonUserTests(object):
    """Common functionality for all users regardless of role or scope."""

    def test_user_can_list_projects(self):
        # This test is assuming the user running it has a role assignment on
        # the project created by ``keystone-manage bootstrap``.
        with self.test_client() as c:
            r = c.get('/v3/projects', headers=self.headers)
            project_ids = []
            for project in r.json['projects']:
                project_ids.append(project['id'])
            self.assertEqual(1, len(r.json['projects']))
            self.assertIn(self.bootstrapper.project_id, project_ids)

    def test_user_can_list_their_projects(self):
        PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id)
        )

        project = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id)
        )

        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.reader_role_id, user_id=self.user_id,
            project_id=project['id']
        )

        with self.test_client() as c:
            r = c.get(
                '/v3/users/%s/projects' % self.user_id, headers=self.headers,
            )
            self.assertEqual(1, len(r.json['projects']))
            self.assertEqual(project['id'], r.json['projects'][0]['id'])

    def test_user_can_get_their_project(self):
        project = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id)
        )

        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.reader_role_id, user_id=self.user_id,
            project_id=project['id']
        )

        with self.test_client() as c:
            r = c.get('/v3/projects/%s' % project['id'], headers=self.headers)
            self.assertEqual(project['id'], r.json['project']['id'])


class _SystemUserTests(object):
    """Common default functionality for all system users."""

    def test_user_can_list_projects(self):
        PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id)
        )

        with self.test_client() as c:
            r = c.get('/v3/projects', headers=self.headers)
            self.assertEqual(2, len(r.json['projects']))

    def test_user_can_list_projects_for_other_users(self):
        project = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id)
        )

        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(
                CONF.identity.default_domain_id,
                id=uuid.uuid4().hex
            )
        )

        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.reader_role_id, user_id=user['id'],
            project_id=project['id']
        )

        with self.test_client() as c:
            r = c.get(
                '/v3/users/%s/projects' % user['id'], headers=self.headers,
            )
            self.assertEqual(1, len(r.json['projects']))
            self.assertEqual(project['id'], r.json['projects'][0]['id'])

    def test_user_can_get_a_project(self):
        project = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id)
        )

        with self.test_client() as c:
            r = c.get('/v3/projects/%s' % project['id'], headers=self.headers)
            self.assertEqual(project['id'], r.json['project']['id'])

    def test_user_cannot_get_non_existant_project_not_found(self):
        with self.test_client() as c:
            c.get(
                '/v3/projects/%s' % uuid.uuid4().hex, headers=self.headers,
                expected_status_code=http_client.NOT_FOUND
            )


class _SystemMemberAndReaderProjectTests(object):
    """Common default functionality for system members and system readers."""

    def test_user_cannot_create_projects(self):
        create = {
            'project': unit.new_project_ref(
                domain_id=CONF.identity.default_domain_id
            )
        }

        with self.test_client() as c:
            c.post(
                '/v3/projects', json=create, headers=self.headers,
                expected_status_code=http_client.FORBIDDEN
            )

    def test_user_cannot_update_projects(self):
        project = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id)
        )

        update = {'project': {'description': uuid.uuid4().hex}}

        with self.test_client() as c:
            c.patch(
                '/v3/projects/%s' % project['id'], json=update,
                headers=self.headers,
                expected_status_code=http_client.FORBIDDEN
            )

    def test_user_cannot_update_non_existant_project_forbidden(self):
        update = {'project': {'description': uuid.uuid4().hex}}

        with self.test_client() as c:
            c.patch(
                '/v3/projects/%s' % uuid.uuid4().hex, json=update,
                headers=self.headers,
                expected_status_code=http_client.FORBIDDEN
            )

    def test_user_cannot_delete_projects(self):
        project = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id)
        )

        with self.test_client() as c:
            c.delete(
                '/v3/projects/%s' % project['id'], headers=self.headers,
                expected_status_code=http_client.FORBIDDEN
            )

    def test_user_cannot_delete_non_existant_project_forbidden(self):
        with self.test_client() as c:
            c.delete(
                '/v3/projects/%s' % uuid.uuid4().hex, headers=self.headers,
                expected_status_code=http_client.FORBIDDEN
            )


class SystemReaderTests(base_classes.TestCaseWithBootstrap,
                        common_auth.AuthTestMixin,
                        _CommonUserTests,
                        _SystemUserTests,
                        _SystemMemberAndReaderProjectTests):

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


class SystemMemberTests(base_classes.TestCaseWithBootstrap,
                        common_auth.AuthTestMixin,
                        _CommonUserTests,
                        _SystemUserTests,
                        _SystemMemberAndReaderProjectTests):

    def setUp(self):
        super(SystemMemberTests, self).setUp()
        self.loadapp()
        self.useFixture(ksfixtures.Policy(self.config_fixture))
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        system_member = unit.new_user_ref(
            domain_id=CONF.identity.default_domain_id
        )
        self.user_id = PROVIDERS.identity_api.create_user(
            system_member
        )['id']
        PROVIDERS.assignment_api.create_system_grant_for_user(
            self.user_id, self.bootstrapper.member_role_id
        )

        auth = self.build_authentication_request(
            user_id=self.user_id, password=system_member['password'],
            system=True
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}
