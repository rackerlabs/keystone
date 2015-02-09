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

from oslo.config import cfg

from keystone.common import controller
from keystone import exception
from keystone import tests
from keystone.tests import test_v3


CONF = cfg.CONF


class ResourceTestCase(test_v3.RestfulTestCase):
    """Test domains and projects."""

    def setUp(self):
        super(ResourceTestCase, self).setUp()

        self.group = self.new_group_ref(
            domain_id=self.domain_id)
        self.group = self.identity_api.create_group(self.group)
        self.group_id = self.group['id']

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
        """Call `POST /domains`` twice with upper() and lower() cased name."""
        ref = self.new_domain_ref()

        # ensure the name is lowercase
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

        # build a request body
        auth_body = self.build_authentication_request(
            user_id=self.user2['id'],
            password=self.user2['password'])

        # sends a request for the user's token
        token_resp = self.post('/auth/tokens', body=auth_body)

        subject_token = token_resp.headers.get('x-subject-token')

        # validates the returned token and it should be valid.
        self.head('/auth/tokens',
                  headers={'x-subject-token': subject_token},
                  expected_status=200)

        # now disable the domain
        self.domain['enabled'] = False
        url = "/domains/%(domain_id)s" % {'domain_id': self.domain['id']}
        self.patch(url,
                   body={'domain': {'enabled': False}},
                   expected_status=200)

        # validates the same token again and it should be 'not found'
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

    def _create_projects_hierarchy(self, hierarchy_size=1):
        """Creates a project hierarchy with specified size.

        :param hierarchy_size: the desired hierarchy size, default is 1 -
                               a project with one child.

        :returns projects: a list of the projects in the created hierarchy.

        """
        resp = self.get(
            '/projects/%(project_id)s' % {
                'project_id': self.project_id})

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

    def test_create_hierarchical_project(self):
        """Call ``POST /projects``."""
        self._create_projects_hierarchy()

    def test_get_project(self):
        """Call ``GET /projects/{project_id}``."""
        r = self.get(
            '/projects/%(project_id)s' % {
                'project_id': self.project_id})
        self.assertValidProjectResponse(r, self.project)

    def test_get_project_with_parents_list(self):
        """Call ``GET /projects/{project_id}?parents_as_list``."""
        projects = self._create_projects_hierarchy(hierarchy_size=2)

        r = self.get(
            '/projects/%(project_id)s?parents_as_list' % {
                'project_id': projects[1]['project']['id']})

        self.assertEqual(1, len(r.result['project']['parents']))
        self.assertValidProjectResponse(r, projects[1]['project'])
        self.assertIn(projects[0], r.result['project']['parents'])
        self.assertNotIn(projects[2], r.result['project']['parents'])

    def test_get_project_with_subtree_list(self):
        """Call ``GET /projects/{project_id}?subtree_as_list``."""
        projects = self._create_projects_hierarchy(hierarchy_size=2)

        r = self.get(
            '/projects/%(project_id)s?subtree_as_list' % {
                'project_id': projects[1]['project']['id']})

        self.assertEqual(1, len(r.result['project']['subtree']))
        self.assertValidProjectResponse(r, projects[1]['project'])
        self.assertNotIn(projects[0], r.result['project']['subtree'])
        self.assertIn(projects[2], r.result['project']['subtree'])

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
        self._create_projects_hierarchy()
        self.delete(
            '/projects/%(project_id)s' % {
                'project_id': self.project_id},
            expected_status=403)


class ResourceV3toV2MethodsTestCase(tests.TestCase):
    """Test domain V3 to V2 conversion methods."""

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
