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

from keystone import exception
from keystone.tests import unit
from keystone.tests.unit import default_fixtures
from keystone.tests.unit.ksfixtures import database


CONF = cfg.CONF
DEFAULT_DOMAIN_ID = CONF.identity.default_domain_id


class TestResourceManager(unit.SQLDriverOverrides, unit.TestCase):

    def setUp(self):
        super(TestResourceManager, self).setUp()
        self.useFixture(database.Database(self.sql_driver_version_overrides))
        self.load_backends()

        # populate the engine with tables & fixtures
        self.load_fixtures(default_fixtures)
        # defaulted by the data load
        self.user_foo['enabled'] = True

    def _create_projects_hierarchy(self, hierarchy_size=2,
                                   domain_id=DEFAULT_DOMAIN_ID,
                                   is_domain=False,
                                   parent_project_id=None):
        """Creates a project hierarchy with specified size.

        :param hierarchy_size: the desired hierarchy size, default is 2 -
                               a project with one child.
        :param domain_id: domain where the projects hierarchy will be created.
        :param is_domain: if the hierarchy will have the is_domain flag active
                          or not.
        :param parent_project_id: if the intention is to create a
            sub-hierarchy, sets the sub-hierarchy root. Defaults to creating
            a new hierarchy, i.e. a new root project.

        :returns projects: a list of the projects in the created hierarchy.

        """
        if parent_project_id:
            project = unit.new_project_ref(parent_id=parent_project_id,
                                           domain_id=domain_id,
                                           is_domain=is_domain)
        else:
            project = unit.new_project_ref(domain_id=domain_id,
                                           is_domain=is_domain)
        project_id = project['id']
        project = self.resource_api.create_project(project_id, project)

        projects = [project]
        for i in range(1, hierarchy_size):
            new_project = unit.new_project_ref(parent_id=project_id,
                                               is_domain=is_domain,
                                               domain_id=domain_id)

            self.resource_api.create_project(new_project['id'], new_project)
            projects.append(new_project)
            project_id = new_project['id']

        return projects

    def test_move_project_with_children_between_domains_fails(self):
        domain1 = unit.new_domain_ref()
        self.resource_api.create_domain(domain1['id'], domain1)
        domain2 = unit.new_domain_ref()
        self.resource_api.create_domain(domain2['id'], domain2)
        project = unit.new_project_ref(domain_id=domain1['id'])
        self.resource_api.create_project(project['id'], project)
        child_project = unit.new_project_ref(domain_id=domain1['id'],
                                             parent_id=project['id'])
        self.resource_api.create_project(child_project['id'], child_project)
        project['domain_id'] = domain2['id']

        # Update is not allowed, since updating the whole subtree would be
        # necessary
        self.assertRaises(exception.ValidationError,
                          self.resource_api.update_project,
                          project['id'],
                          project)

    def test_move_project_not_root_between_domains_fails(self):
        domain1 = unit.new_domain_ref()
        self.resource_api.create_domain(domain1['id'], domain1)
        domain2 = unit.new_domain_ref()
        self.resource_api.create_domain(domain2['id'], domain2)
        project = unit.new_project_ref(domain_id=domain1['id'])
        self.resource_api.create_project(project['id'], project)
        child_project = unit.new_project_ref(domain_id=domain1['id'],
                                             parent_id=project['id'])
        self.resource_api.create_project(child_project['id'], child_project)
        child_project['domain_id'] = domain2['id']

        self.assertRaises(exception.ValidationError,
                          self.resource_api.update_project,
                          child_project['id'],
                          child_project)

    def test_move_root_project_between_domains_succeeds(self):
        domain1 = unit.new_domain_ref()
        self.resource_api.create_domain(domain1['id'], domain1)
        domain2 = unit.new_domain_ref()
        self.resource_api.create_domain(domain2['id'], domain2)
        root_project = unit.new_project_ref(domain_id=domain1['id'],
                                            parent_id=None)
        self.resource_api.create_project(root_project['id'], root_project)

        root_project['domain_id'] = domain2['id']
        self.resource_api.update_project(root_project['id'], root_project)
        project_from_db = self.resource_api.get_project(root_project['id'])

        self.assertEqual(domain2['id'], project_from_db['domain_id'])

    def test_update_domain_id_project_is_domain_fails(self):
        other_domain = unit.new_domain_ref()
        self.resource_api.create_domain(other_domain['id'], other_domain)
        project = unit.new_project_ref(is_domain=True,
                                       domain_id=self.domain_default['id'])
        self.resource_api.create_project(project['id'], project)
        project['domain_id'] = other_domain['id']

        # Update of domain_id of projects acting as domains is not allowed
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

    def test_create_subproject_acting_as_domain_fails(self):
        root_project = unit.new_project_ref(is_domain=True)
        self.resource_api.create_project(root_project['id'], root_project)

        sub_project = unit.new_project_ref(is_domain=True,
                                           parent_id=root_project['id'])

        # Creation of sub projects acting as domains is not allowed yet
        self.assertRaises(exception.ValidationError,
                          self.resource_api.create_project,
                          sub_project['id'], sub_project)

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

    def test_update_cascade_only_accepts_enabled(self):
        # Update cascade does not accept any other attribute but 'enabled'
        new_project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID)
        self.resource_api.create_project(new_project['id'], new_project)

        new_project['name'] = 'project1'
        self.assertRaises(exception.ValidationError,
                          self.resource_api.update_project,
                          new_project['id'],
                          new_project,
                          cascade=True)

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

    def test_delete_hierarchical_not_leaf_project(self):
        projects_hierarchy = self._create_projects_hierarchy()
        root_project = projects_hierarchy[0]

        self.assertRaises(exception.ForbiddenNotSecurity,
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
        self.assertRaises(exception.ForbiddenNotSecurity,
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

    def test_disable_hierarchical_not_leaf_project(self):
        projects_hierarchy = self._create_projects_hierarchy()
        root_project = projects_hierarchy[0]

        root_project['enabled'] = False
        self.assertRaises(exception.ForbiddenNotSecurity,
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
        self.assertRaises(exception.ForbiddenNotSecurity,
                          self.resource_api.update_project,
                          leaf_project['id'],
                          leaf_project)

    def test_cannot_enable_cascade_with_parent_disabled(self):
        projects_hierarchy = self._create_projects_hierarchy(hierarchy_size=3)
        grandparent = projects_hierarchy[0]
        parent = projects_hierarchy[1]

        grandparent['enabled'] = False
        self.resource_api.update_project(grandparent['id'],
                                         grandparent,
                                         cascade=True)
        subtree = self.resource_api.list_projects_in_subtree(parent['id'])
        self.assertFalse(subtree[0]['enabled'])

        parent['enabled'] = True
        self.assertRaises(exception.ForbiddenNotSecurity,
                          self.resource_api.update_project,
                          parent['id'],
                          parent,
                          cascade=True)

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
        self.assertRaises(exception.ForbiddenNotSecurity,
                          self.resource_api.create_project,
                          project['id'],
                          project)

    @unit.skip_if_cache_disabled('resource')
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
