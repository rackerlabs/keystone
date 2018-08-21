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
from keystone.tests.unit import test_v3

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

    def test_user_can_create_credentials_for_themselves(self):
        with self.test_client() as c:
            create = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'type': uuid.uuid4().hex,
                    'user_id': self.system_reader_id
                }
            }
            c.post('/v3/credentials', json=create, headers=self.headers)

    def test_user_can_get_their_credentials(self):
        with self.test_client() as c:
            create = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'type': uuid.uuid4().hex,
                    'user_id': self.system_reader_id
                }
            }
            r = c.post('/v3/credentials', json=create, headers=self.headers)
            credential_id = r.json['credential']['id']

            path = '/v3/credentials/%s' % credential_id
            c.get(path, headers=self.headers)

    def test_user_can_list_their_credentials(self):
        with self.test_client() as c:
            expected = []
            for _ in range(2):
                create = {
                    'credential': {
                        'blob': uuid.uuid4().hex,
                        'type': uuid.uuid4().hex,
                        'user_id': self.system_reader_id
                    }
                }
                r = c.post(
                    '/v3/credentials', json=create, headers=self.headers
                )
                expected.append(r.json['credential'])

            r = c.get('/v3/credentials', headers=self.headers)
            for credential in expected:
                self.assertIn(credential, r.json['credentials'])

    def test_user_can_update_their_credential(self):
        with self.test_client() as c:
            create = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'type': uuid.uuid4().hex,
                    'user_id': self.system_reader_id
                }
            }

            r = c.post('/v3/credentials', json=create, headers=self.headers)
            credential_id = r.json['credential']['id']

            update = {'credential': {'blob': uuid.uuid4().hex}}
            path = '/v3/credentials/%s' % credential_id
            c.patch(path, json=update, headers=self.headers)

    def test_user_can_delete_their_credentials(self):
        with self.test_client() as c:
            create = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'type': uuid.uuid4().hex,
                    'user_id': self.system_reader_id
                }
            }
            r = c.post('/v3/credentials', json=create, headers=self.headers)
            credential_id = r.json['credential']['id']

            path = '/v3/credentials/%s' % credential_id
            c.delete(path, headers=self.headers)

    def test_user_cannot_create_credentials_for_other_users(self):
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        )

        with self.test_client() as c:
            create = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'type': uuid.uuid4().hex,
                    'user_id': user['id']
                }
            }
            c.post(
                '/v3/credentials', json=create, headers=self.headers,
                expected_status_code=http_client.FORBIDDEN
            )

    def test_user_can_list_credentials_for_other_users(self):
        user = unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        user_password = user['password']
        user = PROVIDERS.identity_api.create_user(user)
        project = unit.new_project_ref(
            domain_id=CONF.identity.default_domain_id
        )
        project = PROVIDERS.resource_api.create_project(project['id'], project)
        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.member_role_id, user_id=user['id'],
            project_id=project['id']
        )
        user_auth = self.build_authentication_request(
            user_id=user['id'], password=user_password,
            project_id=project['id']
        )

        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=user_auth)
            token_id = r.headers['X-Subject-Token']
            headers = {'X-Auth-Token': token_id}

            create = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'type': uuid.uuid4().hex,
                    'user_id': user['id']
                }
            }
            r = c.post('/v3/credentials', json=create, headers=headers)
            credential_id = r.json['credential']['id']

        with self.test_client() as c:
            r = c.get('/v3/credentials', json=create, headers=self.headers)
            self.assertEqual(1, len(r.json['credentials']))
            self.assertEqual(credential_id, r.json['credentials'][0]['id'])

    def test_user_cannot_update_credentials_for_others(self):
        user = unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        user_password = user['password']
        user = PROVIDERS.identity_api.create_user(user)
        project = unit.new_project_ref(
            domain_id=CONF.identity.default_domain_id
        )
        project = PROVIDERS.resource_api.create_project(project['id'], project)
        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.member_role_id, user_id=user['id'],
            project_id=project['id']
        )
        user_auth = self.build_authentication_request(
            user_id=user['id'], password=user_password,
            project_id=project['id']
        )

        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=user_auth)
            token_id = r.headers['X-Subject-Token']
            headers = {'X-Auth-Token': token_id}

            create = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'type': uuid.uuid4().hex,
                    'user_id': user['id']
                }
            }
            r = c.post('/v3/credentials', json=create, headers=headers)
            credential_id = r.json['credential']['id']

        with self.test_client() as c:
            update = {'credential': {'blob': uuid.uuid4().hex}}
            path = '/v3/credentials/%s' % credential_id
            c.patch(
                path, json=update, headers=self.headers,
                expected_status_code=http_client.FORBIDDEN
            )

    def test_user_cannot_delete_credentials_for_others(self):
        user = unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        user_password = user['password']
        user = PROVIDERS.identity_api.create_user(user)
        project = unit.new_project_ref(
            domain_id=CONF.identity.default_domain_id
        )
        project = PROVIDERS.resource_api.create_project(project['id'], project)
        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.member_role_id, user_id=user['id'],
            project_id=project['id']
        )
        user_auth = self.build_authentication_request(
            user_id=user['id'], password=user_password,
            project_id=project['id']
        )

        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=user_auth)
            token_id = r.headers['X-Subject-Token']
            headers = {'X-Auth-Token': token_id}

            create = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'type': uuid.uuid4().hex,
                    'user_id': user['id']
                }
            }
            r = c.post('/v3/credentials', json=create, headers=headers)
            credential_id = r.json['credential']['id']

        with self.test_client() as c:
            path = '/v3/credentials/%s' % credential_id
            c.delete(
                path, headers=self.headers,
                expected_status_code=http_client.FORBIDDEN
            )


class SystemMemberTests(base_classes.TestCaseWithBootstrap,
                        common_auth.AuthTestMixin):

    def setUp(self):
        super(SystemMemberTests, self).setUp()
        self.loadapp()
        self.useFixture(ksfixtures.Policy(self.config_fixture))
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        system_member = unit.new_user_ref(
            domain_id=CONF.identity.default_domain_id
        )
        self.system_member_id = PROVIDERS.identity_api.create_user(
            system_member
        )['id']
        PROVIDERS.assignment_api.create_system_grant_for_user(
            self.system_member_id, self.bootstrapper.member_role_id
        )

        auth = self.build_authentication_request(
            user_id=self.system_member_id, password=system_member['password'],
            system=True
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}

    def test_user_can_create_credentials_for_themselves(self):
        with self.test_client() as c:
            create = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'user_id': self.system_member_id,
                    'type': uuid.uuid4().hex
                }
            }
            c.post('/v3/credentials', json=create, headers=self.headers)

    def test_user_can_get_their_credentials(self):
        with self.test_client() as c:
            create = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'type': uuid.uuid4().hex,
                    'user_id': self.system_member_id
                }
            }
            r = c.post('/v3/credentials', json=create, headers=self.headers)
            credential_id = r.json['credential']['id']

            path = '/v3/credentials/%s' % credential_id
            c.get(path, headers=self.headers)

    def test_user_can_list_their_credentials(self):
        with self.test_client() as c:
            expected = []
            for _ in range(2):
                create = {
                    'credential': {
                        'blob': uuid.uuid4().hex,
                        'type': uuid.uuid4().hex,
                        'user_id': self.system_member_id
                    }
                }
                r = c.post(
                    '/v3/credentials', json=create, headers=self.headers
                )
                expected.append(r.json['credential'])

            r = c.get('/v3/credentials', headers=self.headers)
            for credential in expected:
                self.assertIn(credential, r.json['credentials'])

    def test_user_can_update_their_credential(self):
        with self.test_client() as c:
            create = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'type': uuid.uuid4().hex,
                    'user_id': self.system_member_id
                }
            }

            r = c.post('/v3/credentials', json=create, headers=self.headers)
            credential_id = r.json['credential']['id']

            update = {'credential': {'blob': uuid.uuid4().hex}}
            path = '/v3/credentials/%s' % credential_id
            c.patch(path, json=update, headers=self.headers)

    def test_user_can_delete_their_credentials(self):
        with self.test_client() as c:
            create = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'type': uuid.uuid4().hex,
                    'user_id': self.system_member_id
                }
            }
            r = c.post('/v3/credentials', json=create, headers=self.headers)
            credential_id = r.json['credential']['id']

            path = '/v3/credentials/%s' % credential_id
            c.delete(path, headers=self.headers)

    def test_user_cannot_create_credentials_for_other_users(self):
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        )

        with self.test_client() as c:
            create = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'type': uuid.uuid4().hex,
                    'user_id': user['id']
                }
            }
            c.post(
                '/v3/credentials', json=create, headers=self.headers,
                expected_status_code=http_client.FORBIDDEN
            )

    def test_user_can_list_credentials_for_other_users(self):
        user = unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        user_password = user['password']
        user = PROVIDERS.identity_api.create_user(user)
        project = unit.new_project_ref(
            domain_id=CONF.identity.default_domain_id
        )
        project = PROVIDERS.resource_api.create_project(project['id'], project)
        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.member_role_id, user_id=user['id'],
            project_id=project['id']
        )
        user_auth = self.build_authentication_request(
            user_id=user['id'], password=user_password,
            project_id=project['id']
        )

        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=user_auth)
            token_id = r.headers['X-Subject-Token']
            headers = {'X-Auth-Token': token_id}

            create = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'type': uuid.uuid4().hex,
                    'user_id': user['id']
                }
            }
            r = c.post('/v3/credentials', json=create, headers=headers)
            credential_id = r.json['credential']['id']

        with self.test_client() as c:
            r = c.get('/v3/credentials', json=create, headers=self.headers)
            self.assertEqual(1, r.json['credentials'])
            self.assertEqual(credential_id, r.json['credentials'][0]['id'])

    def test_user_can_update_credentials_for_others(self):
        user = unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        user_password = user['password']
        user = PROVIDERS.identity_api.create_user(user)
        project = unit.new_project_ref(
            domain_id=CONF.identity.default_domain_id
        )
        project = PROVIDERS.resource_api.create_project(project['id'], project)
        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.member_role_id, user_id=user['id'],
            project_id=project['id']
        )
        user_auth = self.build_authentication_request(
            user_id=user['id'], password=user_password,
            project_id=project['id']
        )

        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=user_auth)
            token_id = r.headers['X-Subject-Token']
            headers = {'X-Auth-Token': token_id}

            create = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'type': uuid.uuid4().hex,
                    'user_id': user['id']
                }
            }
            r = c.post('/v3/credentials', json=create, headers=headers)
            credential_id = r.json['credential']['id']

        with self.test_client() as c:
            update = {'credential': {'blob': uuid.uuid4().hex}}
            path = '/v3/credentials/%s' % credential_id
            c.patch(path, json=update, headers=self.headers)

    def test_user_cannot_delete_credentials_for_others(self):
        user = unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        user_password = user['password']
        user = PROVIDERS.identity_api.create_user(user)
        project = unit.new_project_ref(
            domain_id=CONF.identity.default_domain_id
        )
        project = PROVIDERS.resource_api.create_project(project['id'], project)
        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.member_role_id, user_id=user['id'],
            project_id=project['id']
        )
        user_auth = self.build_authentication_request(
            user_id=user['id'], password=user_password,
            project_id=project['id']
        )

        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=user_auth)
            token_id = r.headers['X-Subject-Token']
            headers = {'X-Auth-Token': token_id}

            create = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'type': uuid.uuid4().hex,
                    'user_id': user['id']
                }
            }
            r = c.post('/v3/credentials', json=create, headers=headers)
            credential_id = r.json['credential']['id']

        with self.test_client() as c:
            path = '/v3/credentials/%s' % credential_id
            c.delete(
                path, headers=self.headers,
                expected_status_code=http_client.FORBIDDEN
            )


class SystemAdminTests(base_classes.TestCaseWithBootstrap,
                       common_auth.AuthTestMixin):

    def setUp(self):
        super(SystemAdminTests, self).setUp()
        self.loadapp()
        self.useFixture(ksfixtures.Policy(self.config_fixture))
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        # Reuse the system administrator account created during
        # ``keystone-manage bootstrap``
        self.system_admin_id = self.bootstrapper.admin_user_id
        auth = self.build_authentication_request(
            user_id=self.system_admin_id,
            password=self.bootstrapper.admin_password,
            system=True
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}

    def test_user_can_create_credentials_for_themselves(self):
        with self.test_client() as c:
            create = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'user_id': self.system_admin_id,
                    'type': uuid.uuid4().hex
                }
            }
            c.post('/v3/credentials', json=create, headers=self.headers)

    def test_user_can_get_their_credentials(self):
        pass

    def test_user_can_list_their_credentials(self):
        pass

    def test_user_can_update_their_credential(self):
        pass

    def test_user_can_delete_their_credentials(self):
        pass

    def test_user_can_create_credentials_for_other_users(self):
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        )

        with self.test_client() as c:
            create = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'type': uuid.uuid4().hex,
                    'user_id': user['id']
                }
            }
            c.post('/v3/credentials', json=create, headers=self.headers)

    def test_user_can_list_credentials_for_other_users(self):
        user = unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        user_password = user['password']
        user = PROVIDERS.identity_api.create_user(user)
        project = unit.new_project_ref(
            domain_id=CONF.identity.default_domain_id
        )
        project = PROVIDERS.resource_api.create_project(project['id'], project)
        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.member_role_id, user_id=user['id'],
            project_id=project['id']
        )
        user_auth = self.build_authentication_request(
            user_id=user['id'], password=user_password,
            project_id=project['id']
        )

        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=user_auth)
            token_id = r.headers['X-Subject-Token']
            headers = {'X-Auth-Token': token_id}

            create = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'type': uuid.uuid4().hex,
                    'user_id': user['id']
                }
            }
            r = c.post('/v3/credentials', json=create, headers=headers)
            credential_id = r.json['credential']['id']

        with self.test_client() as c:
            r = c.get('/v3/credentials', json=create, headers=self.headers)
            self.assertEqual(1, len(r.json['credentials']))
            self.assertEqual(credential_id, r.json['credentials'][0]['id'])

    def test_user_can_update_credentials_for_others(self):
        user = unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        user_password = user['password']
        user = PROVIDERS.identity_api.create_user(user)
        project = unit.new_project_ref(
            domain_id=CONF.identity.default_domain_id
        )
        project = PROVIDERS.resource_api.create_project(project['id'], project)
        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.member_role_id, user_id=user['id'],
            project_id=project['id']
        )
        user_auth = self.build_authentication_request(
            user_id=user['id'], password=user_password,
            project_id=project['id']
        )

        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=user_auth)
            token_id = r.headers['X-Subject-Token']
            headers = {'X-Auth-Token': token_id}

            create = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'type': uuid.uuid4().hex,
                    'user_id': user['id']
                }
            }
            r = c.post('/v3/credentials', json=create, headers=headers)
            credential_id = r.json['credential']['id']

        with self.test_client() as c:
            path = '/v3/credentials/%s' % credential_id
            update = {'credential': {'blob': uuid.uuid4().hex}}
            c.patch(path, json=update, headers=self.headers)

    def test_user_can_delete_credentials_for_others(self):
        user = unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        user_password = user['password']
        user = PROVIDERS.identity_api.create_user(user)
        project = unit.new_project_ref(
            domain_id=CONF.identity.default_domain_id
        )
        project = PROVIDERS.resource_api.create_project(project['id'], project)
        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.member_role_id, user_id=user['id'],
            project_id=project['id']
        )
        user_auth = self.build_authentication_request(
            user_id=user['id'], password=user_password,
            project_id=project['id']
        )

        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=user_auth)
            token_id = r.headers['X-Subject-Token']
            headers = {'X-Auth-Token': token_id}

            create = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'type': uuid.uuid4().hex,
                    'user_id': user['id']
                }
            }
            r = c.post('/v3/credentials', json=create, headers=headers)
            credential_id = r.json['credential']['id']

        with self.test_client() as c:
            path = '/v3/credentials/%s' % credential_id
            r = c.delete(path, headers=self.headers)


class ProjectReaderTests(test_v3.RestfulTestCase):

    def setUp(self):
        super(ProjectReaderTests, self).setUp()
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        project_reader = unit.new_user_ref(
            domain_id=CONF.identity.default_domain_id
        )
        self.project_reader_id = PROVIDERS.identity_api.create_user(
            project_reader
        )['id']
        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.reader_role_id, user_id=self.project_reader_id,
            project_id=self.project_id
        )

        self.auth = self.build_authentication_request(
            user_id=self.project_reader_id,
            password=project_reader['password'],
            project_id=self.project_id
        )

    def test_user_can_create_credentials_for_themselves(self):
        credential_body = {
            'credential': {
                'blob': uuid.uuid4().hex,
                'user_id': self.project_reader_id,
                'type': uuid.uuid4().hex
            }
        }
        self.post('/credentials', body=credential_body, auth=self.auth)

    def test_user_can_get_a_credential(self):
        pass

    def test_user_can_list_their_credentials(self):
        pass

    def test_user_can_update_their_own_credential(self):
        pass

    def test_user_can_delete_credentials_for_themselves(self):
        pass

    def test_user_cannot_update_credentials_for_others(self):
        pass

    def test_user_cannot_create_credentials_for_others(self):
        pass

    def test_user_cannot_delete_credentials_for_others(self):
        pass


class ProjectMemberTests(ProjectReaderTests):
        pass


class ProjectAdminTests(ProjectReaderTests):
        pass
