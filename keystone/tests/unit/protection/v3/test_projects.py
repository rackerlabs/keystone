# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from six.moves import http_client
import webtest

from keystone.common import provider_api
import keystone.conf
from keystone.tests import unit
from keystone.tests.unit import test_v3
from keystone.tests.unit import utils as test_utils

CONF = keystone.conf.CONF
PROVIDERS = provider_api.ProviderAPIs


class SystemAdministratorTests(object):
    """Authorization test cases for system administrators.

    System administrators can do it all. They are the equivalent of the Most
    Interesting Man In The World, but for the deployment system. Since they
    have the highest authorization on the system, they should be able to
    perform actions regardless of the where in the system the operation is
    taking place.

    """

    def test_system_admin_list_all_projects_succeeds(self):
        response = self.get('/projects', auth=self.system_admin_auth)
        project_list = response.json_body['projects']
        self.assertEqual(3, len(project_list))
        for project in project_list:
            self.assertIn(project['id'], self.project_ids)

    def test_system_admin_get_project_succeeds(self):
        for project_id in self.project_ids:
            path = '/projects/%(project_id)s' % {'project_id': project_id}
            self.get(path, auth=self.system_admin_auth)

    def test_system_admin_create_project_in_domain_succeeds(self):
        project_ref = {
            'project': unit.new_project_ref(
                domain_id=CONF.identity.default_domain_id
            )
        }
        self.post('/projects', body=project_ref, auth=self.system_admin_auth)

        project_ref = {
            'project': unit.new_project_ref(domain_id=self.domain_id)
        }
        self.post('/projects', body=project_ref, auth=self.system_admin_auth)

    def test_system_admin_create_child_project_succeeds(self):
        project_ref = {
            'project': unit.new_project_ref(domain_id=self.domain_id)
        }
        parent_project = self.post(
            '/projects', body=project_ref, auth=self.system_admin_auth
        ).json_body['project']

        project_ref = {
            'project': unit.new_project_ref(
                domain_id=self.domain_id,
                parent_project_id=parent_project['id']
            )
        }
        self.post('/projects', body=project_ref, auth=self.system_admin_auth)

    def test_system_admin_delete_project_succeeds(self):
        for project_id in self.project_ids:
            path = '/projects/%(project_id)s' % {'project_id': project_id}
            self.delete(path, auth=self.system_admin_auth)


class SystemWriterTests(object):

    @test_utils.wip(
        'This test fails because it is waiting for the policy for '
        'identity:get_project to include a `writer` default role.',
        expected_exception=webtest.app.AppError)
    def test_system_writer_list_all_projects_succeeds(self):
        response = self.get('/projects', auth=self.system_writer_auth)
        project_list = response.json_body['projects']
        self.assertEqual(3, len(project_list))
        for project in project_list:
            self.assertIn(project['id'], self.project_ids)

    @test_utils.wip(
        'This test fails because it is waiting for the policy for '
        'identity:get_project to include a `writer` default role.',
        expected_exception=webtest.app.AppError)
    def test_system_writer_get_project_succeeds(self):
        for project_id in self.project_ids:
            path = '/projects/%(project_id)s' % {'project_id': project_id}
            self.get(path, auth=self.system_writer_auth)

    @test_utils.wip(
        'This test fails because it is waiting for the policy for '
        'identity:create_project to include a `writer` default role.',
        expected_exception=webtest.app.AppError)
    def test_system_writer_create_project_in_domain_succeeds(self):
        project_ref = {
            'project': unit.new_project_ref(
                domain_id=CONF.identity.default_domain_id
            )
        }
        self.post('/projects', body=project_ref, auth=self.system_writer_auth)

        project_ref = {
            'project': unit.new_project_ref(domain_id=self.domain_id)
        }
        self.post('/projects', body=project_ref, auth=self.system_writer_auth)

    @test_utils.wip(
        'This test fails because it is waiting for the policy for '
        'identity:create_project to include a `writer` default role.',
        expected_exception=webtest.app.AppError)
    def test_system_writer_create_child_project_succeeds(self):
        project_ref = {
            'project': unit.new_project_ref(domain_id=self.domain_id)
        }
        parent_project = self.post(
            '/projects', body=project_ref, auth=self.system_writer_auth
        ).json_body['project']

        project_ref = {
            'project': unit.new_project_ref(
                domain_id=self.domain_id,
                parent_project_id=parent_project['id']
            )
        }
        self.post('/projects', body=project_ref, auth=self.system_writer_auth)

    def test_system_admin_delete_project_succeeds(self):
        for project_id in self.project_ids:
            path = '/projects/%(project_id)s' % {'project_id': project_id}
            self.delete(path, auth=self.system_writer_auth)


class SystemReaderTests(object):

    @test_utils.wip(
        'This test fails because it is waiting for the policy for '
        'identity:list_project to include a `reader` default role.',
        expected_exception=webtest.app.AppError)
    def test_system_reader_list_all_projects_succeeds(self):
        response = self.get('/projects', auth=self.system_reader_auth)
        project_list = response.json_body['projects']
        self.assertEqual(3, len(project_list))
        for project in project_list:
            self.assertIn(project['id'], self.project_ids)

    @test_utils.wip(
        'This test fails because it is waiting for the policy for '
        'identity:get_project to include a `reader` default role.',
        expected_exception=webtest.app.AppError)
    def test_system_reader_get_project_succeeds(self):
        for project_id in self.project_ids:
            path = '/projects/%(project_id)s' % {'project_id': project_id}
            self.get(path, auth=self.system_reader_auth)

    def test_system_reader_create_project_in_domain_fails(self):
        project_ref = {
            'project': unit.new_project_ref(
                domain_id=CONF.identity.default_domain_id
            )
        }
        self.post(
            '/projects', body=project_ref, auth=self.system_reader_auth,
            expected_status=http_client.FORBIDDEN
        )

        project_ref = {
            'project': unit.new_project_ref(domain_id=self.domain_id)
        }
        self.post(
            '/projects', body=project_ref, auth=self.system_reader_auth,
            expected_status=http_client.FORBIDDEN
        )

    def test_system_reader_delete_project_fails(self):
        for project_id in self.project_ids:
            path = '/projects/%(project_id)s' % {'project_id': project_id}
            self.delete(
                path, auth=self.system_reader_auth,
                expected_status=http_client.FORBIDDEN
            )


class SystemProjectProtectionTests(test_v3.RestfulTestCase,
                                   SystemAdministratorTests,
                                   SystemWriterTests,
                                   SystemReaderTests):

    def setUp(self):
        super(SystemProjectProtectionTests, self).setUp()
        self._create_domains_and_projects()
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

    def load_sample_data(self, create_region_and_endpoints=True,
                         enable_sqlite_foreign_key=False):
        # FIXME(lbragstad): The setup stuff performed here is no different
        # than what operators do when they run `keystone-manage bootstrap`. We
        # should try and find a way to reuse bootstrap in tests rather than
        # rewriting the same thing in setUp classes.

        # create the default domain, put a user in it, and grant that user the
        # 'admin' role on the system
        self._populate_default_domain()
        system_admin = unit.new_user_ref(
            domain_id=CONF.identity.default_domain_id
        )
        system_writer = unit.new_user_ref(
            domain_id=CONF.identity.default_domain_id
        )
        system_reader = unit.new_user_ref(
            domain_id=CONF.identity.default_domain_id
        )
        self.system_admin_password = system_admin['password']
        self.system_writer_password = system_writer['password']
        self.system_reader_password = system_reader['password']

        self.system_admin_id = PROVIDERS.identity_api.create_user(
            system_admin
        )['id']
        self.system_writer_id = PROVIDERS.identity_api.create_user(
            system_writer
        )['id']
        self.system_reader_id = PROVIDERS.identity_api.create_user(
            system_reader
        )['id']

        role = unit.new_role_ref(name='admin')
        role = PROVIDERS.role_api.create_role(role['id'], role)
        self.admin_role_id = role['id']
        PROVIDERS.assignment_api.create_system_grant_for_user(
            self.system_admin_id, self.admin_role_id
        )

        role = unit.new_role_ref(name='writer')
        role = PROVIDERS.role_api.create_role(role['id'], role)
        self.writer_role_id = role['id']
        PROVIDERS.assignment_api.create_system_grant_for_user(
            self.system_writer_id, self.writer_role_id
        )

        role = unit.new_role_ref(name='reader')
        role = PROVIDERS.role_api.create_role(role['id'], role)
        self.reader_role_id = role['id']
        PROVIDERS.assignment_api.create_system_grant_for_user(
            self.system_reader_id, self.reader_role_id
        )

        # This is a specific authentication body for a system scoped token.
        # Passing this to the various self.get, self.put, self.post,
        # self.delete methods will make those methods generate a system-scoped
        # token for the request.
        self.system_admin_auth = self.build_authentication_request(
            user_id=self.system_admin_id, password=self.system_admin_password,
            system=True
        )
        self.system_writer_auth = self.build_authentication_request(
            user_id=self.system_writer_id,
            password=self.system_writer_password,
            system=True
        )
        self.system_reader_auth = self.build_authentication_request(
            user_id=self.system_reader_id,
            password=self.system_reader_password,
            system=True
        )

    def _create_domains_and_projects(self):
        # create a domain
        domain = {'domain': unit.new_domain_ref()}
        domain = self.post(
            '/domains', body=domain, auth=self.system_admin_auth
        ).json_body['domain']

        # create a project in that domain
        project = {'project': unit.new_project_ref(domain_id=domain['id'])}
        project = self.post(
            '/projects', body=project, auth=self.system_admin_auth
        ).json_body['project']

        # create a child project
        child_project = {
            'project': unit.new_project_ref(parent_project_id=project['id'])
        }
        child_project = self.post(
            '/projects', body=child_project, auth=self.system_admin_auth
        ).json_body['project']

        # create a project in the default domain
        default_project = {
            'project': unit.new_project_ref(
                domain_id=CONF.identity.default_domain_id
            )
        }
        default_project = self.post(
            '/projects', body=default_project, auth=self.system_admin_auth
        ).json_body['project']

        self.domain_id = domain['id']
        self.project_id = project['id']
        self.child_project_id = child_project['id']
        self.default_project_id = default_project['id']
        self.project_ids = [
            self.project_id, self.child_project_id, self.default_project_id
        ]
