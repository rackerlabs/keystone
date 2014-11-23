# Copyright 2014 IBM Corp.
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


import copy
import uuid

from keystone.assignment import controllers
from keystone import exception
from keystone import tests
from keystone.tests import default_fixtures
from keystone.tests.ksfixtures import database


CONF = tests.CONF

_ADMIN_CONTEXT = {'is_admin': True, 'query_string': {}}


class TenantTestCase(tests.TestCase):
    """Tests for the V2 Tenant controller.

    These tests exercise :class:`keystone.assignment.controllers.Tenant`.

    """
    def setUp(self):
        super(TenantTestCase, self).setUp()
        self.useFixture(database.Database())
        self.load_backends()
        self.load_fixtures(default_fixtures)
        self.tenant_controller = controllers.Tenant()
        self.role_controller = controllers.Role()

    def test_get_project_users_no_user(self):
        """get_project_users when user doesn't exist.

        When a user that's not known to `identity` has a role on a project,
        then `get_project_users` just skips that user.

        """
        project_id = self.tenant_bar['id']

        orig_project_users = self.tenant_controller.get_project_users(
            _ADMIN_CONTEXT, project_id)

        # Assign a role to a user that doesn't exist to the `bar` project.

        user_id = uuid.uuid4().hex
        self.role_controller.add_role_to_user(
            _ADMIN_CONTEXT, user_id, self.role_other['id'], project_id)

        new_project_users = self.tenant_controller.get_project_users(
            _ADMIN_CONTEXT, project_id)

        # The new user isn't included in the result, so no change.
        # asserting that the expected values appear in the list,
        # without asserting the order of the results
        self.assertEqual(sorted(orig_project_users), sorted(new_project_users))

    def test_list_projects_default_domain(self):
        """Test that list projects only returns those in the default domain."""

        domain = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'enabled': True}
        self.assignment_api.create_domain(domain['id'], domain)
        project1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'domain_id': domain['id']}
        self.assignment_api.create_project(project1['id'], project1)
        # Check the real total number of projects, we should have the above
        # plus those in the default features
        refs = self.assignment_api.list_projects()
        self.assertEqual(len(default_fixtures.TENANTS) + 1, len(refs))

        # Now list all projects using the v2 API - we should only get
        # back those in the default features, since only those are in the
        # default domain.
        refs = self.tenant_controller.get_all_projects(_ADMIN_CONTEXT)
        self.assertEqual(len(default_fixtures.TENANTS), len(refs['tenants']))
        for tenant in default_fixtures.TENANTS:
            tenant_copy = tenant.copy()
            tenant_copy.pop('domain_id')
            self.assertIn(tenant_copy, refs['tenants'])

    def test_create_project_no_name_error(self):
        # When create a project and no name is provided the operation fails
        # with ValidationError.

        project_ref = {}
        self.assertRaises(exception.ValidationError,
                          self.tenant_controller.create_project,
                          _ADMIN_CONTEXT,
                          project_ref)

    def test_update_project(self):
        # A project can be updated.

        project_id = self.tenant_bar['id']
        new_name = self.getUniqueString(prefix='tup')
        project_update = {'name': new_name}

        resp = self.tenant_controller.update_project(
            _ADMIN_CONTEXT, project_id, project_update)

        self.assertEqual(new_name, resp['tenant']['name'])

    def test_delete_project(self):
        # A project can be deleted.

        project_id = self.tenant_bar['id']

        self.tenant_controller.delete_project(_ADMIN_CONTEXT, project_id)

        self.assertRaises(exception.NotFound,
                          self.tenant_controller.get_project,
                          _ADMIN_CONTEXT, project_id)

    def test_get_projects_marker(self):
        # When get_all_projects, can use a marker and only projects after that
        # marker are returned.

        orig_projects = self.tenant_controller.get_all_projects(_ADMIN_CONTEXT)

        marker_idx = 1
        marker = orig_projects['tenants'][marker_idx]['id']

        context = copy.deepcopy(_ADMIN_CONTEXT)
        context['query_string']['marker'] = marker

        projects = self.tenant_controller.get_all_projects(context)

        exp_projects = copy.deepcopy(orig_projects)
        exp_projects['tenants'] = exp_projects['tenants'][marker_idx + 1:]

        self.assertEqual(exp_projects, projects)

    def test_get_projects_unexpected_marker_error(self):
        # When get_all_projects, can use a marker that's not in the response,
        # and the controller raises ValidationError.

        context = copy.deepcopy(_ADMIN_CONTEXT)
        context['query_string']['marker'] = uuid.uuid4().hex

        self.assertRaises(exception.ValidationError,
                          self.tenant_controller.get_all_projects, context)

    def test_get_projects_limit(self):
        # When get_all_projects, can use a limit and get fewer projects.

        orig_projects = self.tenant_controller.get_all_projects(_ADMIN_CONTEXT)

        limit = 1

        context = copy.deepcopy(_ADMIN_CONTEXT)
        context['query_string']['limit'] = '%s' % limit

        projects = self.tenant_controller.get_all_projects(context)

        exp_projects = copy.deepcopy(orig_projects)
        exp_projects['tenants'] = exp_projects['tenants'][0:limit]

        self.assertEqual(exp_projects, projects)

    def test_get_projects_limit_not_int_error(self):
        # When get_all_projects, if limit not an integer then controller raises
        # ValidationError.

        context = copy.deepcopy(_ADMIN_CONTEXT)
        context['query_string']['limit'] = uuid.uuid4().hex

        self.assertRaises(exception.ValidationError,
                          self.tenant_controller.get_all_projects, context)

    def test_get_projects_limit_negative_error(self):
        # When get_all_projects, if limit < 0 controller raises ValidationError

        context = copy.deepcopy(_ADMIN_CONTEXT)
        context['query_string']['limit'] = '-1'

        self.assertRaises(exception.ValidationError,
                          self.tenant_controller.get_all_projects, context)


class RoleTestCase(tests.TestCase):
    """Tests for the V2 Role controller.

    These tests exercise :class:`keystone.assignment.controllers.Role`.

    """

    def setUp(self):
        super(RoleTestCase, self).setUp()
        self.useFixture(database.Database())
        self.load_backends()
        self.load_fixtures(default_fixtures)
        self.role_controller = controllers.Role()

    def test_get_role(self):
        ret = self.role_controller.get_role(_ADMIN_CONTEXT,
                                            self.role_other['id'])
        self.assertEqual({'role': self.role_other}, ret)

    def test_create_role(self):
        role = {'name': self.getUniqueString()}
        ret = self.role_controller.create_role(_ADMIN_CONTEXT, role)

        self.assertIsInstance(ret['role']['id'], str)
        del ret['role']['id']
        self.assertEqual(ret['role'], role)

    def test_create_role_no_name_error(self):
        role = {}
        self.assertRaises(exception.ValidationError,
                          self.role_controller.create_role, _ADMIN_CONTEXT,
                          role)

    def test_create_role_empty_name_error(self):
        role = {'name': ''}
        self.assertRaises(exception.ValidationError,
                          self.role_controller.create_role, _ADMIN_CONTEXT,
                          role)

    def test_get_roles(self):
        ret = self.role_controller.get_roles(_ADMIN_CONTEXT)

        member_role = self.role_controller.get_role(
            _ADMIN_CONTEXT, CONF.member_role_id)['role']
        exp = {'roles': [self.role_admin, self.role_member, member_role,
                         self.role_other, self.role_browser, self.role_writer,
                         self.role_service, ]}
        self.assertEqual(exp, ret)

    def test_remove_role_from_user(self):
        user_id = self.user_foo['id']
        role_id = CONF.member_role_id
        tenant_id = self.tenant_bar['id']
        self.role_controller.remove_role_from_user(_ADMIN_CONTEXT, user_id,
                                                   role_id, tenant_id)

        user_roles = self.role_controller.get_user_roles(_ADMIN_CONTEXT,
                                                         user_id, tenant_id)

        self.assertEqual({'roles': []}, user_roles)
