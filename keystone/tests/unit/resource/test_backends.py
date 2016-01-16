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

from oslo_config import cfg
from six.moves import range

from keystone.common import driver_hints
from keystone import exception
from keystone.tests import unit
from keystone.tests.unit import utils as test_utils


CONF = cfg.CONF
DEFAULT_DOMAIN_ID = CONF.identity.default_domain_id


class ResourceTests(object):

    def test_get_project(self):
        tenant_ref = self.resource_api.get_project(self.tenant_bar['id'])
        self.assertDictEqual(self.tenant_bar, tenant_ref)

    def test_get_project_returns_not_found(self):
        self.assertRaises(exception.ProjectNotFound,
                          self.resource_api.get_project,
                          uuid.uuid4().hex)

    def test_get_project_by_name(self):
        tenant_ref = self.resource_api.get_project_by_name(
            self.tenant_bar['name'],
            DEFAULT_DOMAIN_ID)
        self.assertDictEqual(self.tenant_bar, tenant_ref)

    def test_get_project_by_name_returns_not_found(self):
        self.assertRaises(exception.ProjectNotFound,
                          self.resource_api.get_project_by_name,
                          uuid.uuid4().hex,
                          DEFAULT_DOMAIN_ID)

    def test_create_duplicate_project_id_fails(self):
        project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID)
        project_id = project['id']
        self.resource_api.create_project(project_id, project)
        project['name'] = 'fake2'
        self.assertRaises(exception.Conflict,
                          self.resource_api.create_project,
                          project_id,
                          project)

    def test_create_duplicate_project_name_fails(self):
        project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID)
        project_id = project['id']
        self.resource_api.create_project(project_id, project)
        project['id'] = 'fake2'
        self.assertRaises(exception.Conflict,
                          self.resource_api.create_project,
                          project_id,
                          project)

    def test_create_duplicate_project_name_in_different_domains(self):
        new_domain = unit.new_domain_ref()
        self.resource_api.create_domain(new_domain['id'], new_domain)
        project1 = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID)
        project2 = unit.new_project_ref(name=project1['name'],
                                        domain_id=new_domain['id'])
        self.resource_api.create_project(project1['id'], project1)
        self.resource_api.create_project(project2['id'], project2)

    def test_move_project_between_domains(self):
        domain1 = unit.new_domain_ref()
        self.resource_api.create_domain(domain1['id'], domain1)
        domain2 = unit.new_domain_ref()
        self.resource_api.create_domain(domain2['id'], domain2)
        project = unit.new_project_ref(domain_id=domain1['id'])
        self.resource_api.create_project(project['id'], project)
        project['domain_id'] = domain2['id']
        self.resource_api.update_project(project['id'], project)

        updated_project_ref = self.resource_api.get_project(project['id'])
        self.assertEqual(domain2['id'], updated_project_ref['domain_id'])

    def test_move_project_between_domains_with_clashing_names_fails(self):
        domain1 = unit.new_domain_ref()
        self.resource_api.create_domain(domain1['id'], domain1)
        domain2 = unit.new_domain_ref()
        self.resource_api.create_domain(domain2['id'], domain2)
        # First, create a project in domain1
        project1 = unit.new_project_ref(domain_id=domain1['id'])
        self.resource_api.create_project(project1['id'], project1)
        # Now create a project in domain2 with a potentially clashing
        # name - which should work since we have domain separation
        project2 = unit.new_project_ref(name=project1['name'],
                                        domain_id=domain2['id'])
        self.resource_api.create_project(project2['id'], project2)
        # Now try and move project1 into the 2nd domain - which should
        # fail since the names clash
        project1['domain_id'] = domain2['id']
        self.assertRaises(exception.Conflict,
                          self.resource_api.update_project,
                          project1['id'],
                          project1)

    def test_rename_duplicate_project_name_fails(self):
        project1 = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID)
        project2 = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID)
        self.resource_api.create_project(project1['id'], project1)
        self.resource_api.create_project(project2['id'], project2)
        project2['name'] = project1['name']
        self.assertRaises(exception.Error,
                          self.resource_api.update_project,
                          project2['id'],
                          project2)

    def test_update_project_id_does_nothing(self):
        project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID)
        project_id = project['id']
        self.resource_api.create_project(project['id'], project)
        project['id'] = 'fake2'
        self.resource_api.update_project(project_id, project)
        project_ref = self.resource_api.get_project(project_id)
        self.assertEqual(project_id, project_ref['id'])
        self.assertRaises(exception.ProjectNotFound,
                          self.resource_api.get_project,
                          'fake2')

    def test_delete_domain_with_user_group_project_links(self):
        # TODO(chungg):add test case once expected behaviour defined
        pass

    def test_update_project_returns_not_found(self):
        self.assertRaises(exception.ProjectNotFound,
                          self.resource_api.update_project,
                          uuid.uuid4().hex,
                          dict())

    def test_delete_project_returns_not_found(self):
        self.assertRaises(exception.ProjectNotFound,
                          self.resource_api.delete_project,
                          uuid.uuid4().hex)

    def test_create_update_delete_unicode_project(self):
        unicode_project_name = u'name \u540d\u5b57'
        project = unit.new_project_ref(
            name=unicode_project_name,
            domain_id=CONF.identity.default_domain_id)
        self.resource_api.create_project(project['id'], project)
        self.resource_api.update_project(project['id'], project)
        self.resource_api.delete_project(project['id'])

    def test_create_project_with_no_enabled_field(self):
        ref = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID)
        del ref['enabled']
        self.resource_api.create_project(ref['id'], ref)

        project = self.resource_api.get_project(ref['id'])
        self.assertIs(project['enabled'], True)

    def test_create_project_long_name_fails(self):
        project = unit.new_project_ref(name='a' * 65,
                                       domain_id=DEFAULT_DOMAIN_ID)
        self.assertRaises(exception.ValidationError,
                          self.resource_api.create_project,
                          project['id'],
                          project)

    def test_create_project_blank_name_fails(self):
        project = unit.new_project_ref(name='',
                                       domain_id=DEFAULT_DOMAIN_ID)
        self.assertRaises(exception.ValidationError,
                          self.resource_api.create_project,
                          project['id'],
                          project)

    def test_create_project_invalid_name_fails(self):
        project = unit.new_project_ref(name=None,
                                       domain_id=DEFAULT_DOMAIN_ID)
        self.assertRaises(exception.ValidationError,
                          self.resource_api.create_project,
                          project['id'],
                          project)
        project = unit.new_project_ref(name=123,
                                       domain_id=DEFAULT_DOMAIN_ID)
        self.assertRaises(exception.ValidationError,
                          self.resource_api.create_project,
                          project['id'],
                          project)

    def test_update_project_blank_name_fails(self):
        project = unit.new_project_ref(name='fake1',
                                       domain_id=DEFAULT_DOMAIN_ID)
        self.resource_api.create_project(project['id'], project)
        project['name'] = ''
        self.assertRaises(exception.ValidationError,
                          self.resource_api.update_project,
                          project['id'],
                          project)

    def test_update_project_long_name_fails(self):
        project = unit.new_project_ref(name='fake1',
                                       domain_id=DEFAULT_DOMAIN_ID)
        self.resource_api.create_project(project['id'], project)
        project['name'] = 'a' * 65
        self.assertRaises(exception.ValidationError,
                          self.resource_api.update_project,
                          project['id'],
                          project)

    def test_update_project_invalid_name_fails(self):
        project = unit.new_project_ref(name='fake1',
                                       domain_id=DEFAULT_DOMAIN_ID)
        self.resource_api.create_project(project['id'], project)
        project['name'] = None
        self.assertRaises(exception.ValidationError,
                          self.resource_api.update_project,
                          project['id'],
                          project)

        project['name'] = 123
        self.assertRaises(exception.ValidationError,
                          self.resource_api.update_project,
                          project['id'],
                          project)

    def test_update_project_invalid_enabled_type_string(self):
        project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID)
        self.resource_api.create_project(project['id'], project)
        project_ref = self.resource_api.get_project(project['id'])
        self.assertTrue(project_ref['enabled'])

        # Strings are not valid boolean values
        project['enabled'] = "false"
        self.assertRaises(exception.ValidationError,
                          self.resource_api.update_project,
                          project['id'],
                          project)

    def test_create_project_invalid_enabled_type_string(self):
        project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID,
                                       # invalid string value
                                       enabled="true")
        self.assertRaises(exception.ValidationError,
                          self.resource_api.create_project,
                          project['id'],
                          project)

    def test_create_project_invalid_domain_id(self):
        project = unit.new_project_ref(domain_id=uuid.uuid4().hex)
        self.assertRaises(exception.DomainNotFound,
                          self.resource_api.create_project,
                          project['id'],
                          project)

    def test_list_domains(self):
        domain1 = unit.new_domain_ref()
        domain2 = unit.new_domain_ref()
        self.resource_api.create_domain(domain1['id'], domain1)
        self.resource_api.create_domain(domain2['id'], domain2)
        domains = self.resource_api.list_domains()
        self.assertEqual(3, len(domains))
        domain_ids = []
        for domain in domains:
            domain_ids.append(domain.get('id'))
        self.assertIn(DEFAULT_DOMAIN_ID, domain_ids)
        self.assertIn(domain1['id'], domain_ids)
        self.assertIn(domain2['id'], domain_ids)

    def test_list_projects(self):
        projects = self.resource_api.list_projects()
        self.assertEqual(4, len(projects))
        project_ids = []
        for project in projects:
            project_ids.append(project.get('id'))
        self.assertIn(self.tenant_bar['id'], project_ids)
        self.assertIn(self.tenant_baz['id'], project_ids)

    def test_list_projects_with_multiple_filters(self):
        # Create a project
        project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID)
        self.resource_api.create_project(project['id'], project)

        # Build driver hints with the project's name and inexistent description
        hints = driver_hints.Hints()
        hints.add_filter('name', project['name'])
        hints.add_filter('description', uuid.uuid4().hex)

        # Retrieve projects based on hints and check an empty list is returned
        projects = self.resource_api.list_projects(hints)
        self.assertEqual([], projects)

        # Build correct driver hints
        hints = driver_hints.Hints()
        hints.add_filter('name', project['name'])
        hints.add_filter('description', project['description'])

        # Retrieve projects based on hints
        projects = self.resource_api.list_projects(hints)

        # Check that the returned list contains only the first project
        self.assertEqual(1, len(projects))
        self.assertEqual(project, projects[0])

    def test_list_projects_for_domain(self):
        project_ids = ([x['id'] for x in
                       self.resource_api.list_projects_in_domain(
                           DEFAULT_DOMAIN_ID)])
        self.assertEqual(4, len(project_ids))
        self.assertIn(self.tenant_bar['id'], project_ids)
        self.assertIn(self.tenant_baz['id'], project_ids)
        self.assertIn(self.tenant_mtu['id'], project_ids)
        self.assertIn(self.tenant_service['id'], project_ids)

    @unit.skip_if_no_multiple_domains_support
    def test_list_projects_for_alternate_domain(self):
        domain1 = unit.new_domain_ref()
        self.resource_api.create_domain(domain1['id'], domain1)
        project1 = unit.new_project_ref(domain_id=domain1['id'])
        self.resource_api.create_project(project1['id'], project1)
        project2 = unit.new_project_ref(domain_id=domain1['id'])
        self.resource_api.create_project(project2['id'], project2)
        project_ids = ([x['id'] for x in
                       self.resource_api.list_projects_in_domain(
                           domain1['id'])])
        self.assertEqual(2, len(project_ids))
        self.assertIn(project1['id'], project_ids)
        self.assertIn(project2['id'], project_ids)

    def _create_projects_hierarchy(self, hierarchy_size=2,
                                   domain_id=DEFAULT_DOMAIN_ID,
                                   is_domain=False):
        """Creates a project hierarchy with specified size.

        :param hierarchy_size: the desired hierarchy size, default is 2 -
                               a project with one child.
        :param domain_id: domain where the projects hierarchy will be created.
        :param is_domain: if the hierarchy will have the is_domain flag active
                          or not.

        :returns projects: a list of the projects in the created hierarchy.

        """
        project = unit.new_project_ref(domain_id=domain_id,
                                       is_domain=is_domain)
        project_id = project['id']
        self.resource_api.create_project(project_id, project)

        projects = [project]
        for i in range(1, hierarchy_size):
            new_project = unit.new_project_ref(parent_id=project_id,
                                               is_domain=is_domain,
                                               domain_id=domain_id)

            self.resource_api.create_project(new_project['id'], new_project)
            projects.append(new_project)
            project_id = new_project['id']

        return projects

    @unit.skip_if_no_multiple_domains_support
    def test_create_domain_with_project_api(self):
        project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID,
                                       is_domain=True)
        ref = self.resource_api.create_project(project['id'], project)
        self.assertTrue(ref['is_domain'])
        self.assertEqual(DEFAULT_DOMAIN_ID, ref['domain_id'])

    @unit.skip_if_no_multiple_domains_support
    @test_utils.wip('waiting for sub projects acting as domains support')
    def test_is_domain_sub_project_has_parent_domain_id(self):
        project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID,
                                       is_domain=True)
        self.resource_api.create_project(project['id'], project)

        sub_project = unit.new_project_ref(domain_id=project['id'],
                                           parent_id=project['id'],
                                           is_domain=True)

        ref = self.resource_api.create_project(sub_project['id'], sub_project)
        self.assertTrue(ref['is_domain'])
        self.assertEqual(project['id'], ref['parent_id'])
        self.assertEqual(project['id'], ref['domain_id'])

    @unit.skip_if_no_multiple_domains_support
    @test_utils.wip('waiting for projects acting as domains implementation')
    def test_delete_domain_with_project_api(self):
        project = unit.new_project_ref(domain_id=None,
                                       is_domain=True)
        self.resource_api.create_project(project['id'], project)

        # Try to delete is_domain project that is enabled
        self.assertRaises(exception.ValidationError,
                          self.resource_api.delete_project,
                          project['id'])

        # Disable the project
        project['enabled'] = False
        self.resource_api.update_project(project['id'], project)

        # Successfully delete the project
        self.resource_api.delete_project(project['id'])

    @unit.skip_if_no_multiple_domains_support
    def test_create_subproject_acting_as_domain_fails(self):
        root_project = {'id': uuid.uuid4().hex,
                        'domain_id': DEFAULT_DOMAIN_ID,
                        'name': uuid.uuid4().hex,
                        'parent_id': None,
                        'is_domain': True}
        self.resource_api.create_project(root_project['id'], root_project)

        sub_project = {'id': uuid.uuid4().hex,
                       'domain_id': DEFAULT_DOMAIN_ID,
                       'name': uuid.uuid4().hex,
                       'parent_id': root_project['id'],
                       'is_domain': True}

        # Creation of sub projects acting as domains is not allowed yet
        self.assertRaises(exception.ValidationError,
                          self.resource_api.create_project,
                          sub_project['id'], sub_project)

    @unit.skip_if_no_multiple_domains_support
    def test_create_domain_under_regular_project_hierarchy_fails(self):
        # Projects acting as domains can't have a regular project as parent
        projects_hierarchy = self._create_projects_hierarchy()
        parent = projects_hierarchy[1]
        project = unit.new_project_ref(domain_id=parent['id'],
                                       parent_id=parent['id'],
                                       is_domain=True)

        self.assertRaises(exception.ValidationError,
                          self.resource_api.create_project,
                          project['id'], project)

    @unit.skip_if_no_multiple_domains_support
    @test_utils.wip('waiting for sub projects acting as domains support')
    def test_create_project_under_domain_hierarchy(self):
        projects_hierarchy = self._create_projects_hierarchy(is_domain=True)
        parent = projects_hierarchy[1]
        project = unit.new_project_ref(domain_id=parent['id'],
                                       parent_id=parent['id'],
                                       is_domain=False)

        ref = self.resource_api.create_project(project['id'], project)
        self.assertFalse(ref['is_domain'])
        self.assertEqual(parent['id'], ref['parent_id'])
        self.assertEqual(parent['id'], ref['domain_id'])

    def test_create_project_without_is_domain_flag(self):
        project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID)
        del project['is_domain']
        ref = self.resource_api.create_project(project['id'], project)
        # The is_domain flag should be False by default
        self.assertFalse(ref['is_domain'])

    @unit.skip_if_no_multiple_domains_support
    def test_create_project_passing_is_domain_flag_true(self):
        project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID,
                                       is_domain=True)

        ref = self.resource_api.create_project(project['id'], project)
        self.assertTrue(ref['is_domain'])

    def test_create_project_passing_is_domain_flag_false(self):
        project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID,
                                       is_domain=False)

        ref = self.resource_api.create_project(project['id'], project)
        self.assertIs(False, ref['is_domain'])

    @test_utils.wip('waiting for projects acting as domains implementation')
    def test_create_project_with_parent_id_and_without_domain_id(self):
        project = unit.new_project_ref(domain_id=None)
        self.resource_api.create_project(project['id'], project)

        sub_project = unit.new_project_ref(parent_id=project['id'])
        ref = self.resource_api.create_project(sub_project['id'], sub_project)

        # The domain_id should be set to the parent domain_id
        self.assertEqual(project['domain_id'], ref['domain_id'])

    @test_utils.wip('waiting for projects acting as domains implementation')
    def test_create_project_with_domain_id_and_without_parent_id(self):
        project = unit.new_project_ref(parent_id=None)
        self.resource_api.create_project(project['id'], project)

        sub_project = unit.new_project_ref(domain_id=project['id'])
        ref = self.resource_api.create_project(sub_project['id'], sub_project)

        # The parent_id should be set to the domain_id
        self.assertEqual(project['id'], ref['parent_id'])

    def test_check_leaf_projects(self):
        projects_hierarchy = self._create_projects_hierarchy()
        root_project = projects_hierarchy[0]
        leaf_project = projects_hierarchy[1]

        self.assertFalse(self.resource_api.is_leaf_project(
            root_project['id']))
        self.assertTrue(self.resource_api.is_leaf_project(
            leaf_project['id']))

        # Delete leaf_project
        self.resource_api.delete_project(leaf_project['id'])

        # Now, root_project should be leaf
        self.assertTrue(self.resource_api.is_leaf_project(
            root_project['id']))

    def test_list_projects_in_subtree(self):
        projects_hierarchy = self._create_projects_hierarchy(hierarchy_size=3)
        project1 = projects_hierarchy[0]
        project2 = projects_hierarchy[1]
        project3 = projects_hierarchy[2]
        project4 = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID,
                                        parent_id=project2['id'])
        self.resource_api.create_project(project4['id'], project4)

        subtree = self.resource_api.list_projects_in_subtree(project1['id'])
        self.assertEqual(3, len(subtree))
        self.assertIn(project2, subtree)
        self.assertIn(project3, subtree)
        self.assertIn(project4, subtree)

        subtree = self.resource_api.list_projects_in_subtree(project2['id'])
        self.assertEqual(2, len(subtree))
        self.assertIn(project3, subtree)
        self.assertIn(project4, subtree)

        subtree = self.resource_api.list_projects_in_subtree(project3['id'])
        self.assertEqual(0, len(subtree))

    def test_list_projects_in_subtree_with_circular_reference(self):
        project1 = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID)
        self.resource_api.create_project(project1['id'], project1)

        project2 = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID,
                                        parent_id=project1['id'])
        self.resource_api.create_project(project2['id'], project2)

        project1['parent_id'] = project2['id']  # Adds cyclic reference

        # NOTE(dstanek): The manager does not allow parent_id to be updated.
        # Instead will directly use the driver to create the cyclic
        # reference.
        self.resource_api.driver.update_project(project1['id'], project1)

        subtree = self.resource_api.list_projects_in_subtree(project1['id'])

        # NOTE(dstanek): If a cyclic reference is detected the code bails
        # and returns None instead of falling into the infinite
        # recursion trap.
        self.assertIsNone(subtree)

    def test_list_projects_in_subtree_invalid_project_id(self):
        self.assertRaises(exception.ValidationError,
                          self.resource_api.list_projects_in_subtree,
                          None)

        self.assertRaises(exception.ProjectNotFound,
                          self.resource_api.list_projects_in_subtree,
                          uuid.uuid4().hex)

    def test_list_project_parents(self):
        projects_hierarchy = self._create_projects_hierarchy(hierarchy_size=3)
        project1 = projects_hierarchy[0]
        project2 = projects_hierarchy[1]
        project3 = projects_hierarchy[2]
        project4 = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID,
                                        parent_id=project2['id'])
        self.resource_api.create_project(project4['id'], project4)

        parents1 = self.resource_api.list_project_parents(project3['id'])
        self.assertEqual(2, len(parents1))
        self.assertIn(project1, parents1)
        self.assertIn(project2, parents1)

        parents2 = self.resource_api.list_project_parents(project4['id'])
        self.assertEqual(parents1, parents2)

        parents = self.resource_api.list_project_parents(project1['id'])
        self.assertEqual(0, len(parents))

    def test_list_project_parents_invalid_project_id(self):
        self.assertRaises(exception.ValidationError,
                          self.resource_api.list_project_parents,
                          None)

        self.assertRaises(exception.ProjectNotFound,
                          self.resource_api.list_project_parents,
                          uuid.uuid4().hex)

    def test_delete_project_with_role_assignments(self):
        project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID)
        self.resource_api.create_project(project['id'], project)
        self.assignment_api.add_role_to_user_and_project(
            self.user_foo['id'], project['id'], 'member')
        self.resource_api.delete_project(project['id'])
        self.assertRaises(exception.NotFound,
                          self.resource_api.get_project,
                          project['id'])

    def test_create_project_doesnt_modify_passed_in_dict(self):
        new_project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID)
        original_project = new_project.copy()
        self.resource_api.create_project(new_project['id'], new_project)
        self.assertDictEqual(original_project, new_project)

    def test_update_project_enable(self):
        project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID)
        self.resource_api.create_project(project['id'], project)
        project_ref = self.resource_api.get_project(project['id'])
        self.assertTrue(project_ref['enabled'])

        project['enabled'] = False
        self.resource_api.update_project(project['id'], project)
        project_ref = self.resource_api.get_project(project['id'])
        self.assertEqual(project['enabled'], project_ref['enabled'])

        # If not present, enabled field should not be updated
        del project['enabled']
        self.resource_api.update_project(project['id'], project)
        project_ref = self.resource_api.get_project(project['id'])
        self.assertFalse(project_ref['enabled'])

        project['enabled'] = True
        self.resource_api.update_project(project['id'], project)
        project_ref = self.resource_api.get_project(project['id'])
        self.assertEqual(project['enabled'], project_ref['enabled'])

        del project['enabled']
        self.resource_api.update_project(project['id'], project)
        project_ref = self.resource_api.get_project(project['id'])
        self.assertTrue(project_ref['enabled'])

    def test_create_invalid_domain_fails(self):
        new_group = unit.new_group_ref(domain_id="doesnotexist")
        self.assertRaises(exception.DomainNotFound,
                          self.identity_api.create_group,
                          new_group)
        new_user = unit.new_user_ref(domain_id="doesnotexist")
        self.assertRaises(exception.DomainNotFound,
                          self.identity_api.create_user,
                          new_user)

    @unit.skip_if_no_multiple_domains_support
    def test_project_crud(self):
        domain = unit.new_domain_ref()
        self.resource_api.create_domain(domain['id'], domain)
        project = unit.new_project_ref(domain_id=domain['id'])
        self.resource_api.create_project(project['id'], project)
        project_ref = self.resource_api.get_project(project['id'])
        self.assertDictContainsSubset(project, project_ref)

        project['name'] = uuid.uuid4().hex
        self.resource_api.update_project(project['id'], project)
        project_ref = self.resource_api.get_project(project['id'])
        self.assertDictContainsSubset(project, project_ref)

        self.resource_api.delete_project(project['id'])
        self.assertRaises(exception.ProjectNotFound,
                          self.resource_api.get_project,
                          project['id'])

    def test_domain_delete_hierarchy(self):
        domain = unit.new_domain_ref()
        self.resource_api.create_domain(domain['id'], domain)

        # Creating a root and a leaf project inside the domain
        projects_hierarchy = self._create_projects_hierarchy(
            domain_id=domain['id'])
        root_project = projects_hierarchy[0]
        leaf_project = projects_hierarchy[0]

        # Disable the domain
        domain['enabled'] = False
        self.resource_api.update_domain(domain['id'], domain)

        # Delete the domain
        self.resource_api.delete_domain(domain['id'])

        # Make sure the domain no longer exists
        self.assertRaises(exception.DomainNotFound,
                          self.resource_api.get_domain,
                          domain['id'])

        # Make sure the root project no longer exists
        self.assertRaises(exception.ProjectNotFound,
                          self.resource_api.get_project,
                          root_project['id'])

        # Make sure the leaf project no longer exists
        self.assertRaises(exception.ProjectNotFound,
                          self.resource_api.get_project,
                          leaf_project['id'])

    def test_hierarchical_projects_crud(self):
        # create a hierarchy with just a root project (which is a leaf as well)
        projects_hierarchy = self._create_projects_hierarchy(hierarchy_size=1)
        root_project1 = projects_hierarchy[0]

        # create a hierarchy with one root project and one leaf project
        projects_hierarchy = self._create_projects_hierarchy()
        root_project2 = projects_hierarchy[0]
        leaf_project = projects_hierarchy[1]

        # update description from leaf_project
        leaf_project['description'] = 'new description'
        self.resource_api.update_project(leaf_project['id'], leaf_project)
        proj_ref = self.resource_api.get_project(leaf_project['id'])
        self.assertDictEqual(leaf_project, proj_ref)

        # update the parent_id is not allowed
        leaf_project['parent_id'] = root_project1['id']
        self.assertRaises(exception.ForbiddenAction,
                          self.resource_api.update_project,
                          leaf_project['id'],
                          leaf_project)

        # delete root_project1
        self.resource_api.delete_project(root_project1['id'])
        self.assertRaises(exception.ProjectNotFound,
                          self.resource_api.get_project,
                          root_project1['id'])

        # delete root_project2 is not allowed since it is not a leaf project
        self.assertRaises(exception.ForbiddenAction,
                          self.resource_api.delete_project,
                          root_project2['id'])

    def test_create_project_with_invalid_parent(self):
        project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID,
                                       parent_id='fake')
        self.assertRaises(exception.ProjectNotFound,
                          self.resource_api.create_project,
                          project['id'],
                          project)

    @unit.skip_if_no_multiple_domains_support
    def test_create_leaf_project_with_different_domain(self):
        root_project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID)
        self.resource_api.create_project(root_project['id'], root_project)

        domain = unit.new_domain_ref()
        self.resource_api.create_domain(domain['id'], domain)
        leaf_project = unit.new_project_ref(domain_id=domain['id'],
                                            parent_id=root_project['id'])

        self.assertRaises(exception.ValidationError,
                          self.resource_api.create_project,
                          leaf_project['id'],
                          leaf_project)

    def test_delete_hierarchical_leaf_project(self):
        projects_hierarchy = self._create_projects_hierarchy()
        root_project = projects_hierarchy[0]
        leaf_project = projects_hierarchy[1]

        self.resource_api.delete_project(leaf_project['id'])
        self.assertRaises(exception.ProjectNotFound,
                          self.resource_api.get_project,
                          leaf_project['id'])

        self.resource_api.delete_project(root_project['id'])
        self.assertRaises(exception.ProjectNotFound,
                          self.resource_api.get_project,
                          root_project['id'])

    def test_delete_hierarchical_not_leaf_project(self):
        projects_hierarchy = self._create_projects_hierarchy()
        root_project = projects_hierarchy[0]

        self.assertRaises(exception.ForbiddenAction,
                          self.resource_api.delete_project,
                          root_project['id'])

    def test_update_project_parent(self):
        projects_hierarchy = self._create_projects_hierarchy(hierarchy_size=3)
        project1 = projects_hierarchy[0]
        project2 = projects_hierarchy[1]
        project3 = projects_hierarchy[2]

        # project2 is the parent from project3
        self.assertEqual(project3.get('parent_id'), project2['id'])

        # try to update project3 parent to parent1
        project3['parent_id'] = project1['id']
        self.assertRaises(exception.ForbiddenAction,
                          self.resource_api.update_project,
                          project3['id'],
                          project3)

    def test_create_project_under_disabled_one(self):
        project1 = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID,
                                        enabled=False)
        self.resource_api.create_project(project1['id'], project1)

        project2 = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID,
                                        parent_id=project1['id'])

        # It's not possible to create a project under a disabled one in the
        # hierarchy
        self.assertRaises(exception.ValidationError,
                          self.resource_api.create_project,
                          project2['id'],
                          project2)

    def test_disable_hierarchical_leaf_project(self):
        projects_hierarchy = self._create_projects_hierarchy()
        leaf_project = projects_hierarchy[1]

        leaf_project['enabled'] = False
        self.resource_api.update_project(leaf_project['id'], leaf_project)

        project_ref = self.resource_api.get_project(leaf_project['id'])
        self.assertEqual(leaf_project['enabled'], project_ref['enabled'])

    def test_disable_hierarchical_not_leaf_project(self):
        projects_hierarchy = self._create_projects_hierarchy()
        root_project = projects_hierarchy[0]

        root_project['enabled'] = False
        self.assertRaises(exception.ForbiddenAction,
                          self.resource_api.update_project,
                          root_project['id'],
                          root_project)

    def test_enable_project_with_disabled_parent(self):
        projects_hierarchy = self._create_projects_hierarchy()
        root_project = projects_hierarchy[0]
        leaf_project = projects_hierarchy[1]

        # Disable leaf and root
        leaf_project['enabled'] = False
        self.resource_api.update_project(leaf_project['id'], leaf_project)
        root_project['enabled'] = False
        self.resource_api.update_project(root_project['id'], root_project)

        # Try to enable the leaf project, it's not possible since it has
        # a disabled parent
        leaf_project['enabled'] = True
        self.assertRaises(exception.ForbiddenAction,
                          self.resource_api.update_project,
                          leaf_project['id'],
                          leaf_project)

    def _get_hierarchy_depth(self, project_id):
        return len(self.resource_api.list_project_parents(project_id)) + 1

    def test_check_hierarchy_depth(self):
        # First create a hierarchy with the max allowed depth
        projects_hierarchy = self._create_projects_hierarchy(
            CONF.max_project_tree_depth)
        leaf_project = projects_hierarchy[CONF.max_project_tree_depth - 1]

        depth = self._get_hierarchy_depth(leaf_project['id'])
        self.assertEqual(CONF.max_project_tree_depth, depth)

        # Creating another project in the hierarchy shouldn't be allowed
        project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID,
                                       parent_id=leaf_project['id'])
        self.assertRaises(exception.ForbiddenAction,
                          self.resource_api.create_project,
                          project['id'],
                          project)

    def test_project_update_missing_attrs_with_a_value(self):
        # Creating a project with no description attribute.
        project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID)
        del project['description']
        self.resource_api.create_project(project['id'], project)

        # Add a description attribute.
        project['description'] = uuid.uuid4().hex
        self.resource_api.update_project(project['id'], project)

        project_ref = self.resource_api.get_project(project['id'])
        self.assertDictEqual(project, project_ref)

    def test_project_update_missing_attrs_with_a_falsey_value(self):
        # Creating a project with no description attribute.
        project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID)
        del project['description']
        self.resource_api.create_project(project['id'], project)

        # Add a description attribute.
        project['description'] = ''
        self.resource_api.update_project(project['id'], project)

        project_ref = self.resource_api.get_project(project['id'])
        self.assertDictEqual(project, project_ref)

    def test_domain_crud(self):
        domain = unit.new_domain_ref()
        self.resource_api.create_domain(domain['id'], domain)
        domain_ref = self.resource_api.get_domain(domain['id'])
        self.assertDictEqual(domain, domain_ref)

        domain['name'] = uuid.uuid4().hex
        self.resource_api.update_domain(domain['id'], domain)
        domain_ref = self.resource_api.get_domain(domain['id'])
        self.assertDictEqual(domain, domain_ref)

        # Ensure an 'enabled' domain cannot be deleted
        self.assertRaises(exception.ForbiddenAction,
                          self.resource_api.delete_domain,
                          domain_id=domain['id'])

        # Disable the domain
        domain['enabled'] = False
        self.resource_api.update_domain(domain['id'], domain)

        # Delete the domain
        self.resource_api.delete_domain(domain['id'])

        # Make sure the domain no longer exists
        self.assertRaises(exception.DomainNotFound,
                          self.resource_api.get_domain,
                          domain['id'])

    @unit.skip_if_no_multiple_domains_support
    def test_create_domain_case_sensitivity(self):
        # create a ref with a lowercase name
        ref = unit.new_domain_ref(name=uuid.uuid4().hex.lower())

        self.resource_api.create_domain(ref['id'], ref)

        # assign a new ID with the same name, but this time in uppercase
        ref['id'] = uuid.uuid4().hex
        ref['name'] = ref['name'].upper()
        self.resource_api.create_domain(ref['id'], ref)

    def test_project_attribute_update(self):
        project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID)
        self.resource_api.create_project(project['id'], project)

        # pick a key known to be non-existent
        key = 'description'

        def assert_key_equals(value):
            project_ref = self.resource_api.update_project(
                project['id'], project)
            self.assertEqual(value, project_ref[key])
            project_ref = self.resource_api.get_project(project['id'])
            self.assertEqual(value, project_ref[key])

        def assert_get_key_is(value):
            project_ref = self.resource_api.update_project(
                project['id'], project)
            self.assertIs(project_ref.get(key), value)
            project_ref = self.resource_api.get_project(project['id'])
            self.assertIs(project_ref.get(key), value)

        # add an attribute that doesn't exist, set it to a falsey value
        value = ''
        project[key] = value
        assert_key_equals(value)

        # set an attribute with a falsey value to null
        value = None
        project[key] = value
        assert_get_key_is(value)

        # do it again, in case updating from this situation is handled oddly
        value = None
        project[key] = value
        assert_get_key_is(value)

        # set a possibly-null value to a falsey value
        value = ''
        project[key] = value
        assert_key_equals(value)

        # set a falsey value to a truthy value
        value = uuid.uuid4().hex
        project[key] = value
        assert_key_equals(value)

    @unit.skip_if_cache_disabled('resource')
    @unit.skip_if_no_multiple_domains_support
    def test_domain_rename_invalidates_get_domain_by_name_cache(self):
        domain = unit.new_domain_ref()
        domain_id = domain['id']
        domain_name = domain['name']
        self.resource_api.create_domain(domain_id, domain)
        domain_ref = self.resource_api.get_domain_by_name(domain_name)
        domain_ref['name'] = uuid.uuid4().hex
        self.resource_api.update_domain(domain_id, domain_ref)
        self.assertRaises(exception.DomainNotFound,
                          self.resource_api.get_domain_by_name,
                          domain_name)

    @unit.skip_if_cache_disabled('resource')
    def test_cache_layer_domain_crud(self):
        domain = unit.new_domain_ref()
        domain_id = domain['id']
        # Create Domain
        self.resource_api.create_domain(domain_id, domain)
        domain_ref = self.resource_api.get_domain(domain_id)
        updated_domain_ref = copy.deepcopy(domain_ref)
        updated_domain_ref['name'] = uuid.uuid4().hex
        # Update domain, bypassing resource api manager
        self.resource_api.driver.update_domain(domain_id, updated_domain_ref)
        # Verify get_domain still returns the domain
        self.assertDictContainsSubset(
            domain_ref, self.resource_api.get_domain(domain_id))
        # Invalidate cache
        self.resource_api.get_domain.invalidate(self.resource_api,
                                                domain_id)
        # Verify get_domain returns the updated domain
        self.assertDictContainsSubset(
            updated_domain_ref, self.resource_api.get_domain(domain_id))
        # Update the domain back to original ref, using the assignment api
        # manager
        self.resource_api.update_domain(domain_id, domain_ref)
        self.assertDictContainsSubset(
            domain_ref, self.resource_api.get_domain(domain_id))
        # Make sure domain is 'disabled', bypass resource api manager
        domain_ref_disabled = domain_ref.copy()
        domain_ref_disabled['enabled'] = False
        self.resource_api.driver.update_domain(domain_id,
                                               domain_ref_disabled)
        # Delete domain, bypassing resource api manager
        self.resource_api.driver.delete_domain(domain_id)
        # Verify get_domain still returns the domain
        self.assertDictContainsSubset(
            domain_ref, self.resource_api.get_domain(domain_id))
        # Invalidate cache
        self.resource_api.get_domain.invalidate(self.resource_api,
                                                domain_id)
        # Verify get_domain now raises DomainNotFound
        self.assertRaises(exception.DomainNotFound,
                          self.resource_api.get_domain, domain_id)
        # Recreate Domain
        self.resource_api.create_domain(domain_id, domain)
        self.resource_api.get_domain(domain_id)
        # Make sure domain is 'disabled', bypass resource api manager
        domain['enabled'] = False
        self.resource_api.driver.update_domain(domain_id, domain)
        # Delete domain
        self.resource_api.delete_domain(domain_id)
        # verify DomainNotFound raised
        self.assertRaises(exception.DomainNotFound,
                          self.resource_api.get_domain,
                          domain_id)

    @unit.skip_if_cache_disabled('resource')
    @unit.skip_if_no_multiple_domains_support
    def test_project_rename_invalidates_get_project_by_name_cache(self):
        domain = unit.new_domain_ref()
        project = unit.new_project_ref(domain_id=domain['id'])
        project_id = project['id']
        project_name = project['name']
        self.resource_api.create_domain(domain['id'], domain)
        # Create a project
        self.resource_api.create_project(project_id, project)
        self.resource_api.get_project_by_name(project_name, domain['id'])
        project['name'] = uuid.uuid4().hex
        self.resource_api.update_project(project_id, project)
        self.assertRaises(exception.ProjectNotFound,
                          self.resource_api.get_project_by_name,
                          project_name,
                          domain['id'])

    @unit.skip_if_cache_disabled('resource')
    @unit.skip_if_no_multiple_domains_support
    def test_cache_layer_project_crud(self):
        domain = unit.new_domain_ref()
        project = unit.new_project_ref(domain_id=domain['id'])
        project_id = project['id']
        self.resource_api.create_domain(domain['id'], domain)
        # Create a project
        self.resource_api.create_project(project_id, project)
        self.resource_api.get_project(project_id)
        updated_project = copy.deepcopy(project)
        updated_project['name'] = uuid.uuid4().hex
        # Update project, bypassing resource manager
        self.resource_api.driver.update_project(project_id,
                                                updated_project)
        # Verify get_project still returns the original project_ref
        self.assertDictContainsSubset(
            project, self.resource_api.get_project(project_id))
        # Invalidate cache
        self.resource_api.get_project.invalidate(self.resource_api,
                                                 project_id)
        # Verify get_project now returns the new project
        self.assertDictContainsSubset(
            updated_project,
            self.resource_api.get_project(project_id))
        # Update project using the resource_api manager back to original
        self.resource_api.update_project(project['id'], project)
        # Verify get_project returns the original project_ref
        self.assertDictContainsSubset(
            project, self.resource_api.get_project(project_id))
        # Delete project bypassing resource
        self.resource_api.driver.delete_project(project_id)
        # Verify get_project still returns the project_ref
        self.assertDictContainsSubset(
            project, self.resource_api.get_project(project_id))
        # Invalidate cache
        self.resource_api.get_project.invalidate(self.resource_api,
                                                 project_id)
        # Verify ProjectNotFound now raised
        self.assertRaises(exception.ProjectNotFound,
                          self.resource_api.get_project,
                          project_id)
        # recreate project
        self.resource_api.create_project(project_id, project)
        self.resource_api.get_project(project_id)
        # delete project
        self.resource_api.delete_project(project_id)
        # Verify ProjectNotFound is raised
        self.assertRaises(exception.ProjectNotFound,
                          self.resource_api.get_project,
                          project_id)

    @unit.skip_if_no_multiple_domains_support
    def test_get_default_domain_by_name(self):
        domain_name = 'default'

        domain = unit.new_domain_ref(name=domain_name)
        self.resource_api.create_domain(domain['id'], domain)

        domain_ref = self.resource_api.get_domain_by_name(domain_name)
        self.assertEqual(domain, domain_ref)

    def test_get_not_default_domain_by_name(self):
        domain_name = 'foo'
        self.assertRaises(exception.DomainNotFound,
                          self.resource_api.get_domain_by_name,
                          domain_name)

    def test_project_update_and_project_get_return_same_response(self):
        project = unit.new_project_ref(
            domain_id=CONF.identity.default_domain_id)

        self.resource_api.create_project(project['id'], project)

        updated_project = {'enabled': False}
        updated_project_ref = self.resource_api.update_project(
            project['id'], updated_project)

        # SQL backend adds 'extra' field
        updated_project_ref.pop('extra', None)

        self.assertIs(False, updated_project_ref['enabled'])

        project_ref = self.resource_api.get_project(project['id'])
        self.assertDictEqual(updated_project_ref, project_ref)
