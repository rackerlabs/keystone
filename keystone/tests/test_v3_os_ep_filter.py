# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
#
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

import os
import uuid

from keystone.common.sql import migration
from keystone import config
from keystone import contrib
from keystone.openstack.common import importutils
from keystone.tests import core as test_core

import test_v3


class TestExtensionCase(test_v3.RestfulTestCase):

    FOLDER_EXTENSION_NAME = None
    OS_EXTENSION_NAME = None

    def setUp(self):
        test_core.setup_test_database()
        super(TestExtensionCase, self).setUp()
        self.orig_extension_enablement = getattr(
            config.CONF, self.OS_EXTENSION_NAME).enabled
        self.opt_in_group(self.OS_EXTENSION_NAME, enabled=True)

        package_name = "%s.%s.migrate_repo" % (contrib.__name__,
                                               self.FOLDER_EXTENSION_NAME)

        package = importutils.import_module(package_name)
        self.repo_path = os.path.abspath(
            os.path.dirname(package.__file__))
        migration.db_version_control(version=None, repo_path=self.repo_path)
        migration.db_sync(version=None, repo_path=self.repo_path)

    def tearDown(self):
        super(TestExtensionCase, self).tearDown()
        self.opt_in_group(self.OS_EXTENSION_NAME,
                          enabled=self.orig_extension_enablement)
        #test_core.teardown_test_database()


class EndpointFilterCRUDTestCase(TestExtensionCase):
    """Test OS-EP-FILTER ep/prj associations extension."""

    FOLDER_EXTENSION_NAME = 'endpoint_filter'
    OS_EXTENSION_NAME = 'os_ep_filter'

    # endpoint-project associations crud tests
    # PUT
    def test_create_endpoint_project_assoc(self):
        """PUT /OS-EP-FILTER/projects/{project_id}/endpoints/{endpoint_id}

        Valid endpoint and project id test case.

        """
        self.put('/OS-EP-FILTER/projects/%(project_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                 'project_id': self.default_domain_project_id,
                 'endpoint_id': self.endpoint_id},
                 body='',
                 expected_status=204)

    def test_create_endpoint_project_assoc_noproj(self):
        """PUT OS-EP-FILTER/projects/{project_id}/endpoints/{endpoint_id}

        No valid project id test case.

        """
        self.put('/OS-EP-FILTER/projects/%(project_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                 'project_id': uuid.uuid4().hex,
                 'endpoint_id': self.endpoint_id},
                 body='',
                 expected_status=404)

    def test_create_endpoint_project_assoc_noendp(self):
        """PUT /OS-EP-FILTER/projects/{project_id}/endpoints/{endpoint_id}

        No valid endpoint id test case.

        """
        self.put('/OS-EP-FILTER/projects/%(project_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                 'project_id': self.default_domain_project_id,
                 'endpoint_id': uuid.uuid4().hex},
                 body='',
                 expected_status=404)

    # HEAD
    def test_check_endpoint_project_assoc(self):
        """HEAD /OS-EP-FILTER/projects/{project_id}/endpoints/{endpoint_id}

        Valid project and endpoint id test case.

        """
        self.put('/OS-EP-FILTER/projects/%(project_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                 'project_id': self.default_domain_project_id,
                 'endpoint_id': self.endpoint_id},
                 body='',
                 expected_status=204)
        self.head('/OS-EP-FILTER/projects/%(project_id)s'
                  '/endpoints/%(endpoint_id)s' % {
                  'project_id': self.default_domain_project_id,
                  'endpoint_id': self.endpoint_id},
                  expected_status=204)

    def test_check_endpoint_project_assoc_noproj(self):
        """HEAD /OS-EP-FILTER/projects/{project_id}/endpoints/{endpoint_id}

        No valid project id test case.

        """
        self.put('/OS-EP-FILTER/projects/%(project_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                 'project_id': self.default_domain_project_id,
                 'endpoint_id': self.endpoint_id})
        self.head('/OS-EP-FILTER/projects/%(project_id)s'
                  '/endpoints/%(endpoint_id)s' % {
                  'project_id': uuid.uuid4().hex,
                  'endpoint_id': self.endpoint_id},
                  body='',
                  expected_status=404)

    def test_check_endpoint_project_assoc_noendp(self):
        """HEAD /OS-EP-FILTER/projects/{project_id}/endpoints/{endpoint_id}

        No valid endpoint id test case.

        """
        self.put('/OS-EP-FILTER/projects/%(project_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                 'project_id': self.default_domain_project_id,
                 'endpoint_id': self.endpoint_id})
        self.head('/OS-EP-FILTER/projects/%(project_id)s'
                  '/endpoints/%(endpoint_id)s' % {
                  'project_id': self.default_domain_project_id,
                  'endpoint_id': uuid.uuid4().hex},
                  body='',
                  expected_status=404)

    # GET
    def test_get_endpoint_project_assoc(self):
        """GET /OS-EP-FILTER/projects/{project_id}/endpoints success."""
        self.put('/OS-EP-FILTER/projects/%(project_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                 'project_id': self.default_domain_project_id,
                 'endpoint_id': self.endpoint_id})
        r = self.get('/OS-EP-FILTER/projects/%(project_id)s/endpoints' % {
                     'project_id': self.default_domain_project_id})
        self.assertValidEndpointListResponse(r, self.endpoint)

    def test_get_endpoint_project_assoc_noproj(self):
        """GET /OS-EP-FILTER/projects/{project_id}/endpoints no project."""
        self.put('/OS-EP-FILTER/projects/%(project_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                 'project_id': self.default_domain_project_id,
                 'endpoint_id': self.endpoint_id})
        self.get('/OS-EP-FILTER/projects/%(project_id)s/endpoints' % {
                 'project_id': uuid.uuid4().hex},
                 body='',
                 expected_status=404)

    # DELETE
    def test_remove_endpoint_project_assoc(self):
        """DELETE /OS-EP-FILTER/projects/{project_id}/endpoints/{endpoint_id}

        Valid project id and endpoint id test case.

        """
        self.put('/OS-EP-FILTER/projects/%(project_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                 'project_id': self.default_domain_project_id,
                 'endpoint_id': self.endpoint_id})
        self.delete('/OS-EP-FILTER/projects/%(project_id)s'
                    '/endpoints/%(endpoint_id)s' % {
                    'project_id': self.default_domain_project_id,
                    'endpoint_id': self.endpoint_id},
                    expected_status=204)

    def test_remove_endpoint_project_assoc_noproj(self):
        """DELETE /OS-EP-FILTER/projects/{project_id}/endpoints/{endpoint_id}

        No valid project id test case.

        """
        self.put('/OS-EP-FILTER/projects/%(project_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                 'project_id': self.default_domain_project_id,
                 'endpoint_id': self.endpoint_id},
                 headers={'X-Auth-Token': 'ADMIN'})
        self.delete('/OS-EP-FILTER/projects/%(project_id)s'
                    '/endpoints/%(endpoint_id)s' % {
                    'project_id': uuid.uuid4().hex,
                    'endpoint_id': self.endpoint_id},
                    body='',
                    expected_status=404)

    def test_remove_endpoint_project_assoc_noendp(self):
        """DELETE /OS-EP-FILTER/projects/{project_id}/endpoints/{endpoint_id}

        No valid endpoint id test case.

        """
        self.put('/OS-EP-FILTER/projects/%(project_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                 'project_id': self.default_domain_project_id,
                 'endpoint_id': self.endpoint_id})
        self.delete('/OS-EP-FILTER/projects/%(project_id)s'
                    '/endpoints/%(endpoint_id)s' % {
                    'project_id': self.default_domain_project_id,
                    'endpoint_id': uuid.uuid4().hex},
                    body='',
                    expected_status=404)


class EndpointFilterTestCase(TestExtensionCase):
    """Test OS-EP-FILTER catalog filtering extension."""

    FOLDER_EXTENSION_NAME = 'endpoint_filter'
    OS_EXTENSION_NAME = 'os_ep_filter'

    def test_default_project_id_scoped_token_with_user_id_ep_filter(self):
        # create a second project to work with
        ref = self.new_project_ref(domain_id=self.domain_id)
        r = self.post('/projects', body={'project': ref})
        project = self.assertValidProjectResponse(r, ref)

        # grant the user a role on the project
        self.put(
            '/projects/%(project_id)s/users/%(user_id)s/roles/%(role_id)s' % {
                'user_id': self.user['id'],
                'project_id': project['id'],
                'role_id': self.role['id']})

        # set the user's preferred project
        body = {'user': {'default_project_id': project['id']}}
        r = self.patch('/users/%(user_id)s' % {
            'user_id': self.user['id']},
            body=body)
        self.assertValidUserResponse(r)

        # add one endpoint to the project
        self.put('/OS-EP-FILTER/projects/%(project_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                 'project_id': project['id'],
                 'endpoint_id': self.endpoint_id},
                 body='',
                 expected_status=204)

        # attempt to authenticate without requesting a project
        auth_data = self.build_authentication_request(
            user_id=self.user['id'],
            password=self.user['password'])
        r = self.post('/auth/tokens', body=auth_data)
        self.assertValidProjectScopedTokenResponse(
            r,
            require_catalog=True,
            endpoint_filter=True,
            ep_filter_assoc=1)
        self.assertEqual(r.result['token']['project']['id'], project['id'])

    def test_implicit_project_id_scoped_token_with_user_id_ep_filter(self):
        # attempt to authenticate without requesting a project

        # add one endpoint to default project
        self.put('/OS-EP-FILTER/projects/%(project_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                 'project_id': self.project['id'],
                 'endpoint_id': self.endpoint_id},
                 body='',
                 expected_status=204)

        auth_data = self.build_authentication_request(
            user_id=self.user['id'],
            password=self.user['password'],
            project_id=self.project['id'])
        r = self.post('/auth/tokens', body=auth_data)
        self.assertValidProjectScopedTokenResponse(
            r,
            require_catalog=True,
            endpoint_filter=True,
            ep_filter_assoc=1)
        self.assertEqual(r.result['token']['project']['id'],
                         self.project['id'])

    def test_default_project_id_scoped_token_ep_filter_no_catalog(self):
        # create a second project to work with
        ref = self.new_project_ref(domain_id=self.domain_id)
        r = self.post('/projects', body={'project': ref})
        project = self.assertValidProjectResponse(r, ref)

        # grant the user a role on the project
        self.put(
            '/projects/%(project_id)s/users/%(user_id)s/roles/%(role_id)s' % {
                'user_id': self.user['id'],
                'project_id': project['id'],
                'role_id': self.role['id']})

        # set the user's preferred project
        body = {'user': {'default_project_id': project['id']}}
        r = self.patch('/users/%(user_id)s' % {
            'user_id': self.user['id']},
            body=body)
        self.assertValidUserResponse(r)

        # add one endpoint to the project
        self.put('/OS-EP-FILTER/projects/%(project_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                 'project_id': project['id'],
                 'endpoint_id': self.endpoint_id},
                 body='',
                 expected_status=204)

        # attempt to authenticate without requesting a project
        auth_data = self.build_authentication_request(
            user_id=self.user['id'],
            password=self.user['password'])
        r = self.post('/auth/tokens?nocatalog', body=auth_data)
        self.assertValidProjectScopedTokenResponse(
            r,
            require_catalog=False,
            endpoint_filter=True,
            ep_filter_assoc=1)
        self.assertEqual(r.result['token']['project']['id'], project['id'])

    def test_implicit_project_id_scoped_token_ep_filter_no_catalog(self):
        # attempt to authenticate without requesting a project

        # add one endpoint to default project
        self.put('/OS-EP-FILTER/projects/%(project_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                 'project_id': self.project['id'],
                 'endpoint_id': self.endpoint_id},
                 body='',
                 expected_status=204)

        auth_data = self.build_authentication_request(
            user_id=self.user['id'],
            password=self.user['password'],
            project_id=self.project['id'])
        r = self.post('/auth/tokens?nocatalog', body=auth_data)
        self.assertValidProjectScopedTokenResponse(
            r,
            require_catalog=False,
            endpoint_filter=True,
            ep_filter_assoc=1)
        self.assertEqual(r.result['token']['project']['id'],
                         self.project['id'])
