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

import uuid

from oslo_config import cfg
from six.moves import range

from keystone.common import controller
from keystone import exception
from keystone.tests import unit as tests
from keystone.tests.unit import test_v3


CONF = cfg.CONF


class ResourceTestCase(test_v3.RestfulTestCase):
    """Test domains, projects."""

    def setUp(self):
        super(ResourceTestCase, self).setUp()

        self.group = self.new_group_ref(
            domain_id=self.domain_id)
        self.group = self.identity_api.create_group(self.group)

        self.credential_id = uuid.uuid4().hex
        self.credential = self.new_credential_ref(
            user_id=self.user['id'],
            project_id=self.project_id)
        self.credential['id'] = self.credential_id
        self.credential_api.create_credential(
            self.credential_id,
            self.credential)

    # Domain CRUD tests

    def test_create_domain(self):
        """Call ``POST /domains``."""
        ref = self.new_domain_ref()
        r = self.post(
            '/domains',
            body={'domain': ref})
        return self.assertValidDomainResponse(r, ref)

    def test_create_domain_case_sensitivity(self):
        """Call ``POST /domains`` twice with upper() and lower() cased name."""
        ref = self.new_domain_ref()

        # Ensure the name is lowercase
        ref['name'] = ref['name'].lower()
        r = self.post(
            '/domains',
            body={'domain': ref})
        self.assertValidDomainResponse(r, ref)

        # ensure the name is uppercase
        ref['name'] = ref['name'].upper()
        r = self.post(
            '/domains',
            body={'domain': ref})
        self.assertValidDomainResponse(r, ref)

    def test_create_domain_400(self):
        """Call ``POST /domains``."""
        self.post('/domains', body={'domain': {}}, expected_status=400)

    def test_list_domains(self):
        """Call ``GET /domains``."""
        resource_url = '/domains'
        r = self.get(resource_url)
        self.assertValidDomainListResponse(r, ref=self.domain,
                                           resource_url=resource_url)

    def test_get_domain(self):
        """Call ``GET /domains/{domain_id}``."""
        r = self.get('/domains/%(domain_id)s' % {
            'domain_id': self.domain_id})
        self.assertValidDomainResponse(r, self.domain)

    def test_update_domain(self):
        """Call ``PATCH /domains/{domain_id}``."""
        ref = self.new_domain_ref()
        del ref['id']
        r = self.patch('/domains/%(domain_id)s' % {
            'domain_id': self.domain_id},
            body={'domain': ref})
        self.assertValidDomainResponse(r, ref)

    def test_disable_domain(self):
        """Call ``PATCH /domains/{domain_id}`` (set enabled=False)."""
        # Create a 2nd set of entities in a 2nd domain
        self.domain2 = self.new_domain_ref()
        self.resource_api.create_domain(self.domain2['id'], self.domain2)

        self.project2 = self.new_project_ref(
            domain_id=self.domain2['id'])
        self.resource_api.create_project(self.project2['id'], self.project2)

        self.user2 = self.new_user_ref(
            domain_id=self.domain2['id'],
            project_id=self.project2['id'])
        password = self.user2['password']
        self.user2 = self.identity_api.create_user(self.user2)
        self.user2['password'] = password

        self.assignment_api.add_user_to_project(self.project2['id'],
                                                self.user2['id'])

        # First check a user in that domain can authenticate, via
        # Both v2 and v3
        body = {
            'auth': {
                'passwordCredentials': {
                    'userId': self.user2['id'],
                    'password': self.user2['password']
                },
                'tenantId': self.project2['id']
            }
        }
        self.admin_request(path='/v2.0/tokens', method='POST', body=body)

        auth_data = self.build_authentication_request(
            user_id=self.user2['id'],
            password=self.user2['password'],
            project_id=self.project2['id'])
        self.v3_authenticate_token(auth_data)

        # Now disable the domain
        self.domain2['enabled'] = False
        r = self.patch('/domains/%(domain_id)s' % {
            'domain_id': self.domain2['id']},
            body={'domain': {'enabled': False}})
        self.assertValidDomainResponse(r, self.domain2)

        # Make sure the user can no longer authenticate, via
        # either API
        body = {
            'auth': {
                'passwordCredentials': {
                    'userId': self.user2['id'],
                    'password': self.user2['password']
                },
                'tenantId': self.project2['id']
            }
        }
        self.admin_request(
            path='/v2.0/tokens', method='POST', body=body, expected_status=401)

        # Try looking up in v3 by name and id
        auth_data = self.build_authentication_request(
            user_id=self.user2['id'],
            password=self.user2['password'],
            project_id=self.project2['id'])
        self.v3_authenticate_token(auth_data, expected_status=401)

        auth_data = self.build_authentication_request(
            username=self.user2['name'],
            user_domain_id=self.domain2['id'],
            password=self.user2['password'],
            project_id=self.project2['id'])
        self.v3_authenticate_token(auth_data, expected_status=401)

    def test_delete_enabled_domain_fails(self):
        """Call ``DELETE /domains/{domain_id}`` (when domain enabled)."""

        # Try deleting an enabled domain, which should fail
        self.delete('/domains/%(domain_id)s' % {
            'domain_id': self.domain['id']},
            expected_status=exception.ForbiddenAction.code)

    def test_delete_domain(self):
        """Call ``DELETE /domains/{domain_id}``.

        The sample data set up already has a user, group, project
        and credential that is part of self.domain. Since the user
        we will authenticate with is in this domain, we create a
        another set of entities in a second domain.  Deleting this
        second domain should delete all these new entities. In addition,
        all the entities in the regular self.domain should be unaffected
        by the delete.

        Test Plan:

        - Create domain2 and a 2nd set of entities
        - Disable domain2
        - Delete domain2
        - Check entities in domain2 have been deleted
        - Check entities in self.domain are unaffected

        """

        # Create a 2nd set of entities in a 2nd domain
        self.domain2 = self.new_domain_ref()
        self.resource_api.create_domain(self.domain2['id'], self.domain2)

        self.project2 = self.new_project_ref(
            domain_id=self.domain2['id'])
        self.resource_api.create_project(self.project2['id'], self.project2)

        self.user2 = self.new_user_ref(
            domain_id=self.domain2['id'],
            project_id=self.project2['id'])
        self.user2 = self.identity_api.create_user(self.user2)

        self.group2 = self.new_group_ref(
            domain_id=self.domain2['id'])
        self.group2 = self.identity_api.create_group(self.group2)

        self.credential2 = self.new_credential_ref(
            user_id=self.user2['id'],
            project_id=self.project2['id'])
        self.credential_api.create_credential(
            self.credential2['id'],
            self.credential2)

        # Now disable the new domain and delete it
        self.domain2['enabled'] = False
        r = self.patch('/domains/%(domain_id)s' % {
            'domain_id': self.domain2['id']},
            body={'domain': {'enabled': False}})
        self.assertValidDomainResponse(r, self.domain2)
        self.delete('/domains/%(domain_id)s' % {
            'domain_id': self.domain2['id']})

        # Check all the domain2 relevant entities are gone
        self.assertRaises(exception.DomainNotFound,
                          self.resource_api.get_domain,
                          self.domain2['id'])
        self.assertRaises(exception.ProjectNotFound,
                          self.resource_api.get_project,
                          self.project2['id'])
        self.assertRaises(exception.GroupNotFound,
                          self.identity_api.get_group,
                          self.group2['id'])
        self.assertRaises(exception.UserNotFound,
                          self.identity_api.get_user,
                          self.user2['id'])
        self.assertRaises(exception.CredentialNotFound,
                          self.credential_api.get_credential,
                          self.credential2['id'])

        # ...and that all self.domain entities are still here
        r = self.resource_api.get_domain(self.domain['id'])
        self.assertDictEqual(r, self.domain)
        r = self.resource_api.get_project(self.project['id'])
        self.assertDictEqual(r, self.project)
        r = self.identity_api.get_group(self.group['id'])
        self.assertDictEqual(r, self.group)
        r = self.identity_api.get_user(self.user['id'])
        self.user.pop('password')
        self.assertDictEqual(r, self.user)
        r = self.credential_api.get_credential(self.credential['id'])
        self.assertDictEqual(r, self.credential)

    def test_delete_default_domain_fails(self):
        # Attempting to delete the default domain results in 403 Forbidden.

        # Need to disable it first.
        self.patch('/domains/%(domain_id)s' % {
            'domain_id': CONF.identity.default_domain_id},
            body={'domain': {'enabled': False}})

        self.delete('/domains/%(domain_id)s' % {
            'domain_id': CONF.identity.default_domain_id},
            expected_status=exception.ForbiddenAction.code)

    def test_delete_new_default_domain_fails(self):
        # If change the default domain ID, deleting the new default domain
        # results in a 403 Forbidden.

        # Create a new domain that's not the default
        new_domain = self.new_domain_ref()
        new_domain_id = new_domain['id']
        self.resource_api.create_domain(new_domain_id, new_domain)

        # Disable the new domain so can delete it later.
        self.patch('/domains/%(domain_id)s' % {
            'domain_id': new_domain_id},
            body={'domain': {'enabled': False}})

        # Change the default domain
        self.config_fixture.config(group='identity',
                                   default_domain_id=new_domain_id)

        # Attempt to delete the new domain
        self.delete('/domains/%(domain_id)s' % {'domain_id': new_domain_id},
                    expected_status=exception.ForbiddenAction.code)

    def test_delete_old_default_domain(self):
        # If change the default domain ID, deleting the old default domain
        # works.

        # Create a new domain that's not the default
        new_domain = self.new_domain_ref()
        new_domain_id = new_domain['id']
        self.resource_api.create_domain(new_domain_id, new_domain)

        old_default_domain_id = CONF.identity.default_domain_id

        # Disable the default domain so we can delete it later.
        self.patch('/domains/%(domain_id)s' % {
            'domain_id': old_default_domain_id},
            body={'domain': {'enabled': False}})

        # Change the default domain
        self.config_fixture.config(group='identity',
                                   default_domain_id=new_domain_id)

        # Delete the old default domain
        self.delete(
            '/domains/%(domain_id)s' % {'domain_id': old_default_domain_id})

    def test_token_revoked_once_domain_disabled(self):
        """Test token from a disabled domain has been invalidated.

        Test that a token that was valid for an enabled domain
        becomes invalid once that domain is disabled.

        """

        self.domain = self.new_domain_ref()
        self.resource_api.create_domain(self.domain['id'], self.domain)

        self.user2 = self.new_user_ref(domain_id=self.domain['id'])
        password = self.user2['password']
        self.user2 = self.identity_api.create_user(self.user2)
        self.user2['password'] = password

        # Build a request body
        auth_body = self.build_authentication_request(
            user_id=self.user2['id'],
            password=self.user2['password'])

        # Sends a request for the user's token
        token_resp = self.post('/auth/tokens', body=auth_body)

        subject_token = token_resp.headers.get('x-subject-token')

        # Validates the returned token and it should be valid.
        self.head('/auth/tokens',
                  headers={'x-subject-token': subject_token},
                  expected_status=200)

        # Now disable the domain
        self.domain['enabled'] = False
        url = "/domains/%(domain_id)s" % {'domain_id': self.domain['id']}
        self.patch(url,
                   body={'domain': {'enabled': False}},
                   expected_status=200)

        # Validates the same token again and it should be 'not found'
        # as the domain has already been disabled.
        self.head('/auth/tokens',
                  headers={'x-subject-token': subject_token},
                  expected_status=404)

    def test_delete_domain_hierarchy(self):
        """Call ``DELETE /domains/{domain_id}``."""
        domain = self.new_domain_ref()
        self.resource_api.create_domain(domain['id'], domain)

        root_project = self.new_project_ref(
            domain_id=domain['id'])
        self.resource_api.create_project(root_project['id'], root_project)

        leaf_project = self.new_project_ref(
            domain_id=domain['id'],
            parent_id=root_project['id'])
        self.resource_api.create_project(leaf_project['id'], leaf_project)

        # Need to disable it first.
        self.patch('/domains/%(domain_id)s' % {
            'domain_id': domain['id']},
            body={'domain': {'enabled': False}})

        self.delete(
            '/domains/%(domain_id)s' % {
                'domain_id': domain['id']})

        self.assertRaises(exception.DomainNotFound,
                          self.resource_api.get_domain,
                          domain['id'])

        self.assertRaises(exception.ProjectNotFound,
                          self.resource_api.get_project,
                          root_project['id'])

        self.assertRaises(exception.ProjectNotFound,
                          self.resource_api.get_project,
                          leaf_project['id'])

    def test_forbid_operations_on_federated_domain(self):
        """Make sure one cannot operate on federated domain.

        This includes operations like create, update, delete
        on domain identified by id and name where difference variations of
        id 'Federated' are used.

        """
        def create_domains():
            for variation in ('Federated', 'FEDERATED',
                              'federated', 'fEderated'):
                domain = self.new_domain_ref()
                domain['id'] = variation
                yield domain

        for domain in create_domains():
            self.assertRaises(
                AssertionError, self.assignment_api.create_domain,
                domain['id'], domain)
            self.assertRaises(
                AssertionError, self.assignment_api.update_domain,
                domain['id'], domain)
            self.assertRaises(
                exception.DomainNotFound, self.assignment_api.delete_domain,
                domain['id'])

            # swap 'name' with 'id' and try again, expecting the request to
            # gracefully fail
            domain['id'], domain['name'] = domain['name'], domain['id']
            self.assertRaises(
                AssertionError, self.assignment_api.create_domain,
                domain['id'], domain)
            self.assertRaises(
                AssertionError, self.assignment_api.update_domain,
                domain['id'], domain)
            self.assertRaises(
                exception.DomainNotFound, self.assignment_api.delete_domain,
                domain['id'])

    def test_forbid_operations_on_defined_federated_domain(self):
        """Make sure one cannot operate on a user-defined federated domain.

        This includes operations like create, update, delete.

        """

        non_default_name = 'beta_federated_domain'
        self.config_fixture.config(group='federation',
                                   federated_domain_name=non_default_name)
        domain = self.new_domain_ref()
        domain['name'] = non_default_name
        self.assertRaises(AssertionError,
                          self.assignment_api.create_domain,
                          domain['id'], domain)
        self.assertRaises(exception.DomainNotFound,
                          self.assignment_api.delete_domain,
                          domain['id'])
        self.assertRaises(AssertionError,
                          self.assignment_api.update_domain,
                          domain['id'], domain)

    def test_set_federated_domain_when_config_empty(self):
        """Make sure we are operable even if config value is not properly
        set.

        This includes operations like create, update, delete.

        """
        federated_name = 'Federated'
        self.config_fixture.config(group='federation',
                                   federated_domain_name='')
        domain = self.new_domain_ref()
        domain['id'] = federated_name
        self.assertRaises(AssertionError,
                          self.assignment_api.create_domain,
                          domain['id'], domain)
        self.assertRaises(exception.DomainNotFound,
                          self.assignment_api.delete_domain,
                          domain['id'])
        self.assertRaises(AssertionError,
                          self.assignment_api.update_domain,
                          domain['id'], domain)

        # swap id with name
        domain['id'], domain['name'] = domain['name'], domain['id']
        self.assertRaises(AssertionError,
                          self.assignment_api.create_domain,
                          domain['id'], domain)
        self.assertRaises(exception.DomainNotFound,
                          self.assignment_api.delete_domain,
                          domain['id'])
        self.assertRaises(AssertionError,
                          self.assignment_api.update_domain,
                          domain['id'], domain)

    # Project CRUD tests

    def test_list_projects(self):
        """Call ``GET /projects``."""
        resource_url = '/projects'
        r = self.get(resource_url)
        self.assertValidProjectListResponse(r, ref=self.project,
                                            resource_url=resource_url)

    def test_create_project(self):
        """Call ``POST /projects``."""
        ref = self.new_project_ref(domain_id=self.domain_id)
        r = self.post(
            '/projects',
            body={'project': ref})
        self.assertValidProjectResponse(r, ref)

    def test_create_project_400(self):
        """Call ``POST /projects``."""
        self.post('/projects', body={'project': {}}, expected_status=400)

    def test_create_project_invalid_domain_id(self):
        """Call ``POST /projects``."""
        ref = self.new_project_ref(domain_id=uuid.uuid4().hex)
        self.post('/projects', body={'project': ref}, expected_status=400)

    def _create_projects_hierarchy(self, hierarchy_size=1):
        """Creates a single-branched project hierarchy with the specified size.

        :param hierarchy_size: the desired hierarchy size, default is 1 -
                               a project with one child.

        :returns projects: a list of the projects in the created hierarchy.

        """
        new_ref = self.new_project_ref(domain_id=self.domain_id)
        resp = self.post('/projects', body={'project': new_ref})

        projects = [resp.result]

        for i in range(hierarchy_size):
            new_ref = self.new_project_ref(
                domain_id=self.domain_id,
                parent_id=projects[i]['project']['id'])
            resp = self.post('/projects',
                             body={'project': new_ref})
            self.assertValidProjectResponse(resp, new_ref)

            projects.append(resp.result)

        return projects

    def test_list_projects_filtering_by_parent_id(self):
        """Call ``GET /projects?parent_id={project_id}``."""
        projects = self._create_projects_hierarchy(hierarchy_size=2)

        # Add another child to projects[1] - it will be projects[3]
        new_ref = self.new_project_ref(
            domain_id=self.domain_id,
            parent_id=projects[1]['project']['id'])
        resp = self.post('/projects',
                         body={'project': new_ref})
        self.assertValidProjectResponse(resp, new_ref)

        projects.append(resp.result)

        # Query for projects[0] immediate children - it will
        # be only projects[1]
        r = self.get(
            '/projects?parent_id=%(project_id)s' % {
                'project_id': projects[0]['project']['id']})
        self.assertValidProjectListResponse(r)

        projects_result = r.result['projects']
        expected_list = [projects[1]['project']]

        # projects[0] has projects[1] as child
        self.assertEqual(expected_list, projects_result)

        # Query for projects[1] immediate children - it will
        # be projects[2] and projects[3]
        r = self.get(
            '/projects?parent_id=%(project_id)s' % {
                'project_id': projects[1]['project']['id']})
        self.assertValidProjectListResponse(r)

        projects_result = r.result['projects']
        expected_list = [projects[2]['project'], projects[3]['project']]

        # projects[1] has projects[2] and projects[3] as children
        self.assertEqual(expected_list, projects_result)

        # Query for projects[2] immediate children - it will be an empty list
        r = self.get(
            '/projects?parent_id=%(project_id)s' % {
                'project_id': projects[2]['project']['id']})
        self.assertValidProjectListResponse(r)

        projects_result = r.result['projects']
        expected_list = []

        # projects[2] has no child, projects_result must be an empty list
        self.assertEqual(expected_list, projects_result)

    def test_create_hierarchical_project(self):
        """Call ``POST /projects``."""
        self._create_projects_hierarchy()

    def test_get_project(self):
        """Call ``GET /projects/{project_id}``."""
        r = self.get(
            '/projects/%(project_id)s' % {
                'project_id': self.project_id})
        self.assertValidProjectResponse(r, self.project)

    def test_get_project_with_parents_as_list_with_invalid_id(self):
        """Call ``GET /projects/{project_id}?parents_as_list``."""
        self.get('/projects/%(project_id)s?parents_as_list' % {
                 'project_id': None}, expected_status=404)

        self.get('/projects/%(project_id)s?parents_as_list' % {
                 'project_id': uuid.uuid4().hex}, expected_status=404)

    def test_get_project_with_subtree_as_list_with_invalid_id(self):
        """Call ``GET /projects/{project_id}?subtree_as_list``."""
        self.get('/projects/%(project_id)s?subtree_as_list' % {
                 'project_id': None}, expected_status=404)

        self.get('/projects/%(project_id)s?subtree_as_list' % {
                 'project_id': uuid.uuid4().hex}, expected_status=404)

    def test_get_project_with_parents_as_ids(self):
        """Call ``GET /projects/{project_id}?parents_as_ids``."""
        projects = self._create_projects_hierarchy(hierarchy_size=2)

        # Query for projects[2] parents_as_ids
        r = self.get(
            '/projects/%(project_id)s?parents_as_ids' % {
                'project_id': projects[2]['project']['id']})

        self.assertValidProjectResponse(r, projects[2]['project'])
        parents_as_ids = r.result['project']['parents']

        # Assert parents_as_ids is a structured dictionary correctly
        # representing the hierarchy. The request was made using projects[2]
        # id, hence its parents should be projects[1] and projects[0]. It
        # should have the following structure:
        # {
        #   projects[1]: {
        #       projects[0]: None
        #   }
        # }
        expected_dict = {
            projects[1]['project']['id']: {
                projects[0]['project']['id']: None
            }
        }
        self.assertDictEqual(expected_dict, parents_as_ids)

        # Query for projects[0] parents_as_ids
        r = self.get(
            '/projects/%(project_id)s?parents_as_ids' % {
                'project_id': projects[0]['project']['id']})

        self.assertValidProjectResponse(r, projects[0]['project'])
        parents_as_ids = r.result['project']['parents']

        # projects[0] has no parents, parents_as_ids must be None
        self.assertIsNone(parents_as_ids)

    def test_get_project_with_parents_as_list_and_parents_as_ids(self):
        """Call ``GET /projects/{project_id}?parents_as_list&parents_as_ids``.

        """
        projects = self._create_projects_hierarchy(hierarchy_size=2)

        self.get(
            '/projects/%(project_id)s?parents_as_list&parents_as_ids' % {
                'project_id': projects[1]['project']['id']},
            expected_status=400)

    def test_get_project_with_subtree_as_ids(self):
        """Call ``GET /projects/{project_id}?subtree_as_ids``.

        This test creates a more complex hierarchy to test if the structured
        dictionary returned by using the ``subtree_as_ids`` query param
        correctly represents the hierarchy.

        The hierarchy contains 5 projects with the following structure::

                                  +--A--+
                                  |     |
                               +--B--+  C
                               |     |
                               D     E


        """
        projects = self._create_projects_hierarchy(hierarchy_size=2)

        # Add another child to projects[0] - it will be projects[3]
        new_ref = self.new_project_ref(
            domain_id=self.domain_id,
            parent_id=projects[0]['project']['id'])
        resp = self.post('/projects',
                         body={'project': new_ref})
        self.assertValidProjectResponse(resp, new_ref)
        projects.append(resp.result)

        # Add another child to projects[1] - it will be projects[4]
        new_ref = self.new_project_ref(
            domain_id=self.domain_id,
            parent_id=projects[1]['project']['id'])
        resp = self.post('/projects',
                         body={'project': new_ref})
        self.assertValidProjectResponse(resp, new_ref)
        projects.append(resp.result)

        # Query for projects[0] subtree_as_ids
        r = self.get(
            '/projects/%(project_id)s?subtree_as_ids' % {
                'project_id': projects[0]['project']['id']})
        self.assertValidProjectResponse(r, projects[0]['project'])
        subtree_as_ids = r.result['project']['subtree']

        # The subtree hierarchy from projects[0] should have the following
        # structure:
        # {
        #   projects[1]: {
        #       projects[2]: None,
        #       projects[4]: None
        #   },
        #   projects[3]: None
        # }
        expected_dict = {
            projects[1]['project']['id']: {
                projects[2]['project']['id']: None,
                projects[4]['project']['id']: None
            },
            projects[3]['project']['id']: None
        }
        self.assertDictEqual(expected_dict, subtree_as_ids)

        # Now query for projects[1] subtree_as_ids
        r = self.get(
            '/projects/%(project_id)s?subtree_as_ids' % {
                'project_id': projects[1]['project']['id']})
        self.assertValidProjectResponse(r, projects[1]['project'])
        subtree_as_ids = r.result['project']['subtree']

        # The subtree hierarchy from projects[1] should have the following
        # structure:
        # {
        #   projects[2]: None,
        #   projects[4]: None
        # }
        expected_dict = {
            projects[2]['project']['id']: None,
            projects[4]['project']['id']: None
        }
        self.assertDictEqual(expected_dict, subtree_as_ids)

        # Now query for projects[3] subtree_as_ids
        r = self.get(
            '/projects/%(project_id)s?subtree_as_ids' % {
                'project_id': projects[3]['project']['id']})
        self.assertValidProjectResponse(r, projects[3]['project'])
        subtree_as_ids = r.result['project']['subtree']

        # projects[3] has no subtree, subtree_as_ids must be None
        self.assertIsNone(subtree_as_ids)

    def test_get_project_with_subtree_as_list_and_subtree_as_ids(self):
        """Call ``GET /projects/{project_id}?subtree_as_list&subtree_as_ids``.

        """
        projects = self._create_projects_hierarchy(hierarchy_size=2)

        self.get(
            '/projects/%(project_id)s?subtree_as_list&subtree_as_ids' % {
                'project_id': projects[1]['project']['id']},
            expected_status=400)

    def test_update_project(self):
        """Call ``PATCH /projects/{project_id}``."""
        ref = self.new_project_ref(domain_id=self.domain_id)
        del ref['id']
        r = self.patch(
            '/projects/%(project_id)s' % {
                'project_id': self.project_id},
            body={'project': ref})
        self.assertValidProjectResponse(r, ref)

    def test_update_project_domain_id(self):
        """Call ``PATCH /projects/{project_id}`` with domain_id."""
        project = self.new_project_ref(domain_id=self.domain['id'])
        self.resource_api.create_project(project['id'], project)
        project['domain_id'] = CONF.identity.default_domain_id
        r = self.patch('/projects/%(project_id)s' % {
            'project_id': project['id']},
            body={'project': project},
            expected_status=exception.ValidationError.code)
        self.config_fixture.config(domain_id_immutable=False)
        project['domain_id'] = self.domain['id']
        r = self.patch('/projects/%(project_id)s' % {
            'project_id': project['id']},
            body={'project': project})
        self.assertValidProjectResponse(r, project)

    def test_update_project_parent_id(self):
        """Call ``PATCH /projects/{project_id}``."""
        projects = self._create_projects_hierarchy()
        leaf_project = projects[1]['project']
        leaf_project['parent_id'] = None
        self.patch(
            '/projects/%(project_id)s' % {
                'project_id': leaf_project['id']},
            body={'project': leaf_project},
            expected_status=403)

    def test_disable_leaf_project(self):
        """Call ``PATCH /projects/{project_id}``."""
        projects = self._create_projects_hierarchy()
        leaf_project = projects[1]['project']
        leaf_project['enabled'] = False
        r = self.patch(
            '/projects/%(project_id)s' % {
                'project_id': leaf_project['id']},
            body={'project': leaf_project})
        self.assertEqual(
            leaf_project['enabled'], r.result['project']['enabled'])

    def test_disable_not_leaf_project(self):
        """Call ``PATCH /projects/{project_id}``."""
        projects = self._create_projects_hierarchy()
        root_project = projects[0]['project']
        root_project['enabled'] = False
        self.patch(
            '/projects/%(project_id)s' % {
                'project_id': root_project['id']},
            body={'project': root_project},
            expected_status=403)

    def test_delete_project(self):
        """Call ``DELETE /projects/{project_id}``

        As well as making sure the delete succeeds, we ensure
        that any credentials that reference this projects are
        also deleted, while other credentials are unaffected.

        """
        # First check the credential for this project is present
        r = self.credential_api.get_credential(self.credential['id'])
        self.assertDictEqual(r, self.credential)

        # Create a second credential with a different project
        self.project2 = self.new_project_ref(
            domain_id=self.domain['id'])
        self.resource_api.create_project(self.project2['id'], self.project2)
        self.credential2 = self.new_credential_ref(
            user_id=self.user['id'],
            project_id=self.project2['id'])
        self.credential_api.create_credential(
            self.credential2['id'],
            self.credential2)

        # Now delete the project
        self.delete(
            '/projects/%(project_id)s' % {
                'project_id': self.project_id})

        # Deleting the project should have deleted any credentials
        # that reference this project
        self.assertRaises(exception.CredentialNotFound,
                          self.credential_api.get_credential,
                          credential_id=self.credential['id'])

        # But the credential for project2 is unaffected
        r = self.credential_api.get_credential(self.credential2['id'])
        self.assertDictEqual(r, self.credential2)

    def test_delete_not_leaf_project(self):
        """Call ``DELETE /projects/{project_id}``."""
        projects = self._create_projects_hierarchy()
        self.delete(
            '/projects/%(project_id)s' % {
                'project_id': projects[0]['project']['id']},
            expected_status=403)


class DomainProjectV3toV2MethodsTestCase(tests.TestCase):
    """Test domain V3 to V2 conversion methods."""
    def _setup_initial_projects(self):
        self.project_id = uuid.uuid4().hex
        self.domain_id = uuid.uuid4().hex
        self.parent_id = uuid.uuid4().hex

        # Project with only domain_id in ref
        self.project1 = {'id': self.project_id,
                         'name': self.project_id,
                         'domain_id': self.domain_id}

        # Project with both domain_id and parent_id in ref
        self.project2 = {'id': self.project_id,
                         'name': self.project_id,
                         'domain_id': self.domain_id,
                         'parent_id': self.parent_id}

        # Project with no domain_id and parent_id in ref
        self.project3 = {'id': self.project_id,
                         'name': self.project_id,
                         'domain_id': self.domain_id,
                         'parent_id': self.parent_id}

        # Expected result with no domain_id and parent_id
        self.expected_project = {'id': self.project_id,
                                 'name': self.project_id}

    def test_v2controller_filter_domain_id(self):
        # V2.0 is not domain aware, ensure domain_id is popped off the ref.
        other_data = uuid.uuid4().hex
        domain_id = uuid.uuid4().hex
        ref = {'domain_id': domain_id,
               'other_data': other_data}

        ref_no_domain = {'other_data': other_data}
        expected_ref = ref_no_domain.copy()

        updated_ref = controller.V2Controller.filter_domain_id(ref)
        self.assertIs(ref, updated_ref)
        self.assertDictEqual(ref, expected_ref)

        # Make sure we don't error/muck up data if domain_id isn't present
        updated_ref = controller.V2Controller.filter_domain_id(ref_no_domain)
        self.assertIs(ref_no_domain, updated_ref)
        self.assertDictEqual(ref_no_domain, expected_ref)

    def test_v3controller_filter_domain_id(self):
        # No data should be filtered out in this case.
        other_data = uuid.uuid4().hex
        domain_id = uuid.uuid4().hex
        ref = {'domain_id': domain_id,
               'other_data': other_data}

        expected_ref = ref.copy()
        updated_ref = controller.V3Controller.filter_domain_id(ref)
        self.assertIs(ref, updated_ref)
        self.assertDictEqual(ref, expected_ref)

    def test_v2controller_filter_domain(self):
        other_data = uuid.uuid4().hex
        domain_id = uuid.uuid4().hex
        non_default_domain_ref = {'domain': {'id': domain_id},
                                  'other_data': other_data}
        default_domain_ref = {'domain': {'id': 'default'},
                              'other_data': other_data}
        updated_ref = controller.V2Controller.filter_domain(default_domain_ref)
        self.assertNotIn('domain', updated_ref)
        self.assertRaises(exception.Unauthorized,
                          controller.V2Controller.filter_domain,
                          non_default_domain_ref)

    def test_v2controller_filter_project_parent_id(self):
        # V2.0 is not project hierarchy aware, ensure parent_id is popped off.
        other_data = uuid.uuid4().hex
        parent_id = uuid.uuid4().hex
        ref = {'parent_id': parent_id,
               'other_data': other_data}

        ref_no_parent = {'other_data': other_data}
        expected_ref = ref_no_parent.copy()

        updated_ref = controller.V2Controller.filter_project_parent_id(ref)
        self.assertIs(ref, updated_ref)
        self.assertDictEqual(ref, expected_ref)

        # Make sure we don't error/muck up data if parent_id isn't present
        updated_ref = controller.V2Controller.filter_project_parent_id(
            ref_no_parent)
        self.assertIs(ref_no_parent, updated_ref)
        self.assertDictEqual(ref_no_parent, expected_ref)

    def test_v3_to_v2_project_method(self):
        self._setup_initial_projects()
        updated_project1 = controller.V2Controller.v3_to_v2_project(
            self.project1)
        self.assertIs(self.project1, updated_project1)
        self.assertDictEqual(self.project1, self.expected_project)
        updated_project2 = controller.V2Controller.v3_to_v2_project(
            self.project2)
        self.assertIs(self.project2, updated_project2)
        self.assertDictEqual(self.project2, self.expected_project)
        updated_project3 = controller.V2Controller.v3_to_v2_project(
            self.project3)
        self.assertIs(self.project3, updated_project3)
        self.assertDictEqual(self.project3, self.expected_project)

    def test_v3_to_v2_project_method_list(self):
        self._setup_initial_projects()
        project_list = [self.project1, self.project2, self.project3]
        updated_list = controller.V2Controller.v3_to_v2_project(project_list)

        self.assertEqual(len(updated_list), len(project_list))

        for i, ref in enumerate(updated_list):
            # Order should not change.
            self.assertIs(ref, project_list[i])

        self.assertDictEqual(self.project1, self.expected_project)
        self.assertDictEqual(self.project2, self.expected_project)
        self.assertDictEqual(self.project3, self.expected_project)
