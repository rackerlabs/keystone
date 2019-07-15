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


class _TestCaseWithBootstrapAppCred(base_classes.TestCaseWithBootstrap):
    """Bootstrap with an application credential for testing."""

    def setUp(self):
        super(_TestCaseWithBootstrapAppCred, self).setUp()

        # bootstrap a user with app credential
        new_user_ref = unit.new_user_ref(
            domain_id=CONF.identity.default_domain_id
        )
        app_cred_user_ref = PROVIDERS.identity_api.create_user(
            new_user_ref
        )
        self.app_cred_user_id = app_cred_user_ref['id']
        self.app_cred_user_password = new_user_ref['password']
        app_cred_project_ref = PROVIDERS.resource_api.create_project(
            uuid.uuid4().hex,
            unit.new_project_ref(domain_id=CONF.identity.default_domain_id)
        )
        self.app_cred_project_id = app_cred_project_ref['id']
        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.member_role_id,
            user_id=self.app_cred_user_id,
            project_id=app_cred_project_ref['id']
        )
        self.app_cred_user_token = None

    def _auth_app_cred_user(self):
        if not self.app_cred_user_token:
            # auth as app credential test user and create an app credential
            auth = self.build_authentication_request(
                user_id=self.app_cred_user_id,
                password=self.app_cred_user_password,
                project_id=self.app_cred_project_id
            )
            with self.test_client() as c:
                r = c.post('/v3/auth/tokens', json=auth)
                self.app_cred_user_token = r.headers['X-Subject-Token']

    def _create_application_credential(self):
        self._auth_app_cred_user()

        app_cred_body = {
            'application_credential': unit.new_application_credential_ref()
        }

        with self.test_client() as c:
            r = c.post(
                '/v3/users/%s/application_credentials' % self.app_cred_user_id,
                json=app_cred_body,
                expected_status_code=http_client.CREATED,
                headers={'X-Auth-Token': self.app_cred_user_token})
            return r.json['application_credential']


class _DomainAndProjectUserTests(object):
    """Domain and project user tests.

    Domain and project users should not be able to manage application
    credentials other then their own.
    """

    def test_user_cannot_list_application_credentials(self):
        # create a couple of application credentials
        self._create_application_credential()
        self._create_application_credential()

        with self.test_client() as c:
            c.get('/v3/users/%s/application_credentials' % (
                  self.app_cred_user_id),
                  expected_status_code=http_client.FORBIDDEN,
                  headers=self.headers)

    def test_user_cannot_get_application_credential(self):
        app_cred = self._create_application_credential()

        with self.test_client() as c:
            c.get('/v3/users/%s/application_credentials/%s' % (
                  self.app_cred_user_id,
                  app_cred['id']),
                  expected_status_code=http_client.FORBIDDEN,
                  headers=self.headers)

    def test_user_cannot_lookup_application_credential(self):
        app_cred = self._create_application_credential()

        with self.test_client() as c:
            c.get('/v3/users/%s/application_credentials?name=%s' % (
                  self.app_cred_user_id,
                  app_cred['name']),
                  expected_status_code=http_client.FORBIDDEN,
                  headers=self.headers)

    def test_user_cannot_create_app_credential_for_another_user(self):
        app_cred_body = {
            'application_credential': unit.new_application_credential_ref(
                roles=[{'id': self.bootstrapper.member_role_id}])
        }

        with self.test_client() as c:
            c.post(
                '/v3/users/%s/application_credentials' % self.app_cred_user_id,
                json=app_cred_body,
                expected_status_code=http_client.FORBIDDEN,
                headers=self.headers)

    def test_user_cannot_delete_application_credential(self):
        app_cred = self._create_application_credential()

        with self.test_client() as c:
            c.delete(
                '/v3/users/%s/application_credentials/%s' % (
                    self.app_cred_user_id,
                    app_cred['id']),
                expected_status_code=http_client.FORBIDDEN,
                headers=self.headers)


class _SystemUserTests(object):
    """Common default functionality for all system users."""

    def test_user_can_list_application_credentials(self):
        # create a couple of application credentials
        self._create_application_credential()
        self._create_application_credential()

        with self.test_client() as c:
            r = c.get(
                '/v3/users/%s/application_credentials' % (
                    self.app_cred_user_id),
                headers=self.headers)
            self.assertEqual(2, len(r.json['application_credentials']))

    def test_user_can_get_application_credential(self):
        app_cred = self._create_application_credential()

        with self.test_client() as c:
            r = c.get(
                '/v3/users/%s/application_credentials/%s' % (
                    self.app_cred_user_id,
                    app_cred['id']),
                headers=self.headers)
            actual_app_cred = r.json['application_credential']
            self.assertEqual(app_cred['id'], actual_app_cred['id'])

    def test_user_can_lookup_application_credential(self):
        app_cred = self._create_application_credential()

        with self.test_client() as c:
            r = c.get(
                '/v3/users/%s/application_credentials?name=%s' % (
                    self.app_cred_user_id,
                    app_cred['name']),
                headers=self.headers)
            self.assertEqual(1, len(r.json['application_credentials']))
            actual_app_cred = r.json['application_credentials'][0]
            self.assertEqual(app_cred['id'], actual_app_cred['id'])

    def test_user_cannot_create_app_credential_for_another_user(self):
        # make sure we are not operating under the same user
        self.assertNotEqual(self.user_id, self.app_cred_user_id)

        app_cred_body = {
            'application_credential': unit.new_application_credential_ref(
                roles=[{'id': self.bootstrapper.member_role_id}])
        }

        with self.test_client() as c:
            c.post(
                '/v3/users/%s/application_credentials' % self.app_cred_user_id,
                json=app_cred_body,
                expected_status_code=http_client.FORBIDDEN,
                headers=self.headers)

    def _test_delete_application_credential(
            self,
            expected_status_code=http_client.NO_CONTENT):
        app_cred = self._create_application_credential()

        with self.test_client() as c:
            c.delete(
                '/v3/users/%s/application_credentials/%s' % (
                    self.app_cred_user_id,
                    app_cred['id']),
                expected_status_code=expected_status_code,
                headers=self.headers)


class SystemReaderTests(_TestCaseWithBootstrapAppCred,
                        common_auth.AuthTestMixin,
                        _SystemUserTests):

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

    def test_system_reader_cannot_delete_application_credential_for_user(self):
        self._test_delete_application_credential(
            expected_status_code=http_client.FORBIDDEN)


class SystemMemberTests(_TestCaseWithBootstrapAppCred,
                        common_auth.AuthTestMixin,
                        _SystemUserTests):

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

    def test_system_reader_cannot_delete_application_credential_for_user(self):
        self._test_delete_application_credential(
            expected_status_code=http_client.FORBIDDEN)


class SystemAdminTests(_TestCaseWithBootstrapAppCred,
                       common_auth.AuthTestMixin,
                       _SystemUserTests):

    def setUp(self):
        super(SystemAdminTests, self).setUp()
        self.loadapp()
        self.useFixture(ksfixtures.Policy(self.config_fixture))
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        self.user_id = self.bootstrapper.admin_user_id
        auth = self.build_authentication_request(
            user_id=self.user_id,
            password=self.bootstrapper.admin_password,
            system=True
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}

    def test_system_admin_can_delete_application_credential_for_user(self):
        self._test_delete_application_credential()


class DomainAdminTests(_TestCaseWithBootstrapAppCred,
                       common_auth.AuthTestMixin,
                       _DomainAndProjectUserTests):

    def setUp(self):
        super(DomainAdminTests, self).setUp()
        self.loadapp()
        self.useFixture(ksfixtures.Policy(self.config_fixture))
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        domain_admin = unit.new_user_ref(
            domain_id=CONF.identity.default_domain_id)
        self.user_id = PROVIDERS.identity_api.create_user(domain_admin)['id']
        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.admin_role_id, user_id=self.user_id,
            domain_id=CONF.identity.default_domain_id
        )

        auth = self.build_authentication_request(
            user_id=self.user_id, password=domain_admin['password'],
            domain_id=CONF.identity.default_domain_id
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}


class ProjectAdminTests(_TestCaseWithBootstrapAppCred,
                        common_auth.AuthTestMixin,
                        _DomainAndProjectUserTests):

    def setUp(self):
        super(ProjectAdminTests, self).setUp()
        self.loadapp()
        self.useFixture(ksfixtures.Policy(self.config_fixture))
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        project_admin = unit.new_user_ref(
            domain_id=CONF.identity.default_domain_id)
        self.user_id = PROVIDERS.identity_api.create_user(project_admin)['id']
        # even project admin of project where the app credential
        # is intended for cannot perform app credential operations
        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.admin_role_id,
            user_id=self.user_id,
            project_id=self.app_cred_project_id
        )
        auth = self.build_authentication_request(
            user_id=self.user_id, password=project_admin['password'],
            project_id=self.app_cred_project_id
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}
