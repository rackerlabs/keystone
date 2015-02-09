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

from keystone.tests import test_v3


CONF = cfg.CONF


def _build_role_assignment_url_and_entity(
        role_id, user_id=None, group_id=None, domain_id=None,
        project_id=None, inherited_to_projects=False,
        effective=False):

    if user_id and domain_id:
        url = ('/domains/%(domain_id)s/users/%(user_id)s'
               '/roles/%(role_id)s' % {
                   'domain_id': domain_id,
                   'user_id': user_id,
                   'role_id': role_id})
        entity = {'role': {'id': role_id},
                  'user': {'id': user_id},
                  'scope': {'domain': {'id': domain_id}}}
    elif user_id and project_id:
        url = ('/projects/%(project_id)s/users/%(user_id)s'
               '/roles/%(role_id)s' % {
                   'project_id': project_id,
                   'user_id': user_id,
                   'role_id': role_id})
        entity = {'role': {'id': role_id},
                  'user': {'id': user_id},
                  'scope': {'project': {'id': project_id}}}
    if group_id and domain_id:
        url = ('/domains/%(domain_id)s/groups/%(group_id)s'
               '/roles/%(role_id)s' % {
                   'domain_id': domain_id,
                   'group_id': group_id,
                   'role_id': role_id})
        entity = {'role': {'id': role_id},
                  'group': {'id': group_id},
                  'scope': {'domain': {'id': domain_id}}}
    elif group_id and project_id:
        url = ('/projects/%(project_id)s/groups/%(group_id)s'
               '/roles/%(role_id)s' % {
                   'project_id': project_id,
                   'group_id': group_id,
                   'role_id': role_id})
        entity = {'role': {'id': role_id},
                  'group': {'id': group_id},
                  'scope': {'project': {'id': project_id}}}
    if inherited_to_projects:
        url = '/OS-INHERIT%s/inherited_to_projects' % url
        if not effective:
            entity['scope']['OS-INHERIT:inherited_to'] = 'projects'
    return (url, entity)


class AssignmentTestCase(test_v3.RestfulTestCase):
    """Test roles and role assignments."""

    def setUp(self):
        super(AssignmentTestCase, self).setUp()

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

    # Role CRUD tests

    def test_create_role(self):
        """Call ``POST /roles``."""
        ref = self.new_role_ref()
        r = self.post(
            '/roles',
            body={'role': ref})
        return self.assertValidRoleResponse(r, ref)

    def test_create_role_400(self):
        """Call ``POST /roles``."""
        self.post('/roles', body={'role': {}}, expected_status=400)

    def test_list_roles(self):
        """Call ``GET /roles``."""
        resource_url = '/roles'
        r = self.get(resource_url)
        self.assertValidRoleListResponse(r, ref=self.role,
                                         resource_url=resource_url)

    def test_get_role(self):
        """Call ``GET /roles/{role_id}``."""
        r = self.get('/roles/%(role_id)s' % {
            'role_id': self.role_id})
        self.assertValidRoleResponse(r, self.role)

    def test_update_role(self):
        """Call ``PATCH /roles/{role_id}``."""
        ref = self.new_role_ref()
        del ref['id']
        r = self.patch('/roles/%(role_id)s' % {
            'role_id': self.role_id},
            body={'role': ref})
        self.assertValidRoleResponse(r, ref)

    def test_delete_role(self):
        """Call ``DELETE /roles/{role_id}``."""
        self.delete('/roles/%(role_id)s' % {
            'role_id': self.role_id})

    # Role Grants tests

    def test_crud_user_project_role_grants(self):
        collection_url = (
            '/projects/%(project_id)s/users/%(user_id)s/roles' % {
                'project_id': self.project['id'],
                'user_id': self.user['id']})
        member_url = '%(collection_url)s/%(role_id)s' % {
            'collection_url': collection_url,
            'role_id': self.role_id}

        self.put(member_url)
        self.head(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, ref=self.role,
                                         resource_url=collection_url)

        # FIXME(gyee): this test is no longer valid as user
        # have no role in the project. Can't get a scoped token
        # self.delete(member_url)
        # r = self.get(collection_url)
        # self.assertValidRoleListResponse(r, expected_length=0)
        # self.assertIn(collection_url, r.result['links']['self'])

    def test_crud_user_project_role_grants_no_user(self):
        """Grant role on a project to a user that doesn't exist, 404 result.

        When grant a role on a project to a user that doesn't exist, the server
        returns 404 Not Found for the user.

        """

        user_id = uuid.uuid4().hex

        collection_url = (
            '/projects/%(project_id)s/users/%(user_id)s/roles' % {
                'project_id': self.project['id'], 'user_id': user_id})
        member_url = '%(collection_url)s/%(role_id)s' % {
            'collection_url': collection_url,
            'role_id': self.role_id}

        self.put(member_url, expected_status=404)

    def test_crud_user_domain_role_grants(self):
        collection_url = (
            '/domains/%(domain_id)s/users/%(user_id)s/roles' % {
                'domain_id': self.domain_id,
                'user_id': self.user['id']})
        member_url = '%(collection_url)s/%(role_id)s' % {
            'collection_url': collection_url,
            'role_id': self.role_id}

        self.put(member_url)
        self.head(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, ref=self.role,
                                         resource_url=collection_url)

        self.delete(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, expected_length=0,
                                         resource_url=collection_url)

    def test_crud_user_domain_role_grants_no_user(self):
        """Grant role on a domain to a user that doesn't exist, 404 result.

        When grant a role on a domain to a user that doesn't exist, the server
        returns 404 Not Found for the user.

        """

        user_id = uuid.uuid4().hex

        collection_url = (
            '/domains/%(domain_id)s/users/%(user_id)s/roles' % {
                'domain_id': self.domain_id, 'user_id': user_id})
        member_url = '%(collection_url)s/%(role_id)s' % {
            'collection_url': collection_url,
            'role_id': self.role_id}

        self.put(member_url, expected_status=404)

    def test_crud_group_project_role_grants(self):
        collection_url = (
            '/projects/%(project_id)s/groups/%(group_id)s/roles' % {
                'project_id': self.project_id,
                'group_id': self.group_id})
        member_url = '%(collection_url)s/%(role_id)s' % {
            'collection_url': collection_url,
            'role_id': self.role_id}

        self.put(member_url)
        self.head(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, ref=self.role,
                                         resource_url=collection_url)

        self.delete(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, expected_length=0,
                                         resource_url=collection_url)

    def test_crud_group_project_role_grants_no_group(self):
        """Grant role on a project to a group that doesn't exist, 404 result.

        When grant a role on a project to a group that doesn't exist, the
        server returns 404 Not Found for the group.

        """

        group_id = uuid.uuid4().hex

        collection_url = (
            '/projects/%(project_id)s/groups/%(group_id)s/roles' % {
                'project_id': self.project_id,
                'group_id': group_id})
        member_url = '%(collection_url)s/%(role_id)s' % {
            'collection_url': collection_url,
            'role_id': self.role_id}

        self.put(member_url, expected_status=404)

    def test_crud_group_domain_role_grants(self):
        collection_url = (
            '/domains/%(domain_id)s/groups/%(group_id)s/roles' % {
                'domain_id': self.domain_id,
                'group_id': self.group_id})
        member_url = '%(collection_url)s/%(role_id)s' % {
            'collection_url': collection_url,
            'role_id': self.role_id}

        self.put(member_url)
        self.head(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, ref=self.role,
                                         resource_url=collection_url)

        self.delete(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, expected_length=0,
                                         resource_url=collection_url)

    def test_crud_group_domain_role_grants_no_group(self):
        """Grant role on a domain to a group that doesn't exist, 404 result.

        When grant a role on a domain to a group that doesn't exist, the server
        returns 404 Not Found for the group.

        """

        group_id = uuid.uuid4().hex

        collection_url = (
            '/domains/%(domain_id)s/groups/%(group_id)s/roles' % {
                'domain_id': self.domain_id,
                'group_id': group_id})
        member_url = '%(collection_url)s/%(role_id)s' % {
            'collection_url': collection_url,
            'role_id': self.role_id}

        self.put(member_url, expected_status=404)

    def _create_new_user_and_assign_role_on_project(self):
        """Create a new user and assign user a role on a project."""
        # Create a new user
        new_user = self.new_user_ref(domain_id=self.domain_id)
        user_ref = self.identity_api.create_user(new_user)
        # Assign the user a role on the project
        collection_url = (
            '/projects/%(project_id)s/users/%(user_id)s/roles' % {
                'project_id': self.project_id,
                'user_id': user_ref['id']})
        member_url = ('%(collection_url)s/%(role_id)s' % {
            'collection_url': collection_url,
            'role_id': self.role_id})
        self.put(member_url, expected_status=204)
        # Check the user has the role assigned
        self.head(member_url, expected_status=204)
        return member_url, user_ref

    def test_delete_user_before_removing_role_assignment_succeeds(self):
        """Call ``DELETE`` on the user before the role assignment."""
        member_url, user = self._create_new_user_and_assign_role_on_project()
        # Delete the user from identity backend
        self.identity_api.driver.delete_user(user['id'])
        # Clean up the role assignment
        self.delete(member_url, expected_status=204)
        # Make sure the role is gone
        self.head(member_url, expected_status=404)

    def test_delete_user_and_check_role_assignment_fails(self):
        """Call ``DELETE`` on the user and check the role assignment."""
        member_url, user = self._create_new_user_and_assign_role_on_project()
        # Delete the user from identity backend
        self.identity_api.driver.delete_user(user['id'])
        # We should get a 404 when looking for the user in the identity
        # backend because we're not performing a delete operation on the role.
        self.head(member_url, expected_status=404)

    def test_token_revoked_once_group_role_grant_revoked(self):
        """Test token is revoked when group role grant is revoked

        When a role granted to a group is revoked for a given scope,
        all tokens related to this scope and belonging to one of the members
        of this group should be revoked.

        The revocation should be independently to the presence
        of the revoke API.
        """

        # If enabled, the revoke API will revoke tokens first.
        # This ensures that tokens are revoked even without revoke API.
        self.assignment_api.revoke_api = None

        # creates grant from group on project.
        self.assignment_api.create_grant(role_id=self.role['id'],
                                         project_id=self.project['id'],
                                         group_id=self.group['id'])

        # adds user to the group.
        self.identity_api.add_user_to_group(user_id=self.user['id'],
                                            group_id=self.group['id'])

        # creates a token for the user
        auth_body = self.build_authentication_request(
            user_id=self.user['id'],
            password=self.user['password'],
            project_id=self.project['id'])
        token_resp = self.post('/auth/tokens', body=auth_body)
        token = token_resp.headers.get('x-subject-token')

        # validates the returned token; it should be valid.
        self.head('/auth/tokens',
                  headers={'x-subject-token': token},
                  expected_status=200)

        # revokes the grant from group on project.
        self.assignment_api.delete_grant(role_id=self.role['id'],
                                         project_id=self.project['id'],
                                         group_id=self.group['id'])

        # validates the same token again; it should not longer be valid.
        self.head('/auth/tokens',
                  headers={'x-subject-token': token},
                  expected_status=404)

    # Role Assignments tests

    def test_get_role_assignments(self):
        """Call ``GET /role_assignments``.

        The sample data set up already has a user, group and project
        that is part of self.domain. We use these plus a new user
        we create as our data set, making sure we ignore any
        role assignments that are already in existence.

        Since we don't yet support a first class entity for role
        assignments, we are only testing the LIST API.  To create
        and delete the role assignments we use the old grant APIs.

        Test Plan:

        - Create extra user for tests
        - Get a list of all existing role assignments
        - Add a new assignment for each of the four combinations, i.e.
          group+domain, user+domain, group+project, user+project, using
          the same role each time
        - Get a new list of all role assignments, checking these four new
          ones have been added
        - Then delete the four we added
        - Get a new list of all role assignments, checking the four have
          been removed

        """

        # Since the default fixtures already assign some roles to the
        # user it creates, we also need a new user that will not have any
        # existing assignments
        self.user1 = self.new_user_ref(
            domain_id=self.domain['id'])
        self.user1 = self.identity_api.create_user(self.user1)

        collection_url = '/role_assignments'
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r,
                                                   resource_url=collection_url)
        existing_assignments = len(r.result.get('role_assignments'))

        # Now add one of each of the four types of assignment, making sure
        # that we get them all back.
        gd_url, gd_entity = _build_role_assignment_url_and_entity(
            domain_id=self.domain_id, group_id=self.group_id,
            role_id=self.role_id)
        self.put(gd_url)
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(
            r,
            expected_length=existing_assignments + 1,
            resource_url=collection_url)
        self.assertRoleAssignmentInListResponse(r, gd_entity, link_url=gd_url)

        ud_url, ud_entity = _build_role_assignment_url_and_entity(
            domain_id=self.domain_id, user_id=self.user1['id'],
            role_id=self.role_id)
        self.put(ud_url)
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(
            r,
            expected_length=existing_assignments + 2,
            resource_url=collection_url)
        self.assertRoleAssignmentInListResponse(r, ud_entity, link_url=ud_url)

        gp_url, gp_entity = _build_role_assignment_url_and_entity(
            project_id=self.project_id, group_id=self.group_id,
            role_id=self.role_id)
        self.put(gp_url)
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(
            r,
            expected_length=existing_assignments + 3,
            resource_url=collection_url)
        self.assertRoleAssignmentInListResponse(r, gp_entity, link_url=gp_url)

        up_url, up_entity = _build_role_assignment_url_and_entity(
            project_id=self.project_id, user_id=self.user1['id'],
            role_id=self.role_id)
        self.put(up_url)
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(
            r,
            expected_length=existing_assignments + 4,
            resource_url=collection_url)
        self.assertRoleAssignmentInListResponse(r, up_entity, link_url=up_url)

        # Now delete the four we added and make sure they are removed
        # from the collection.

        self.delete(gd_url)
        self.delete(ud_url)
        self.delete(gp_url)
        self.delete(up_url)
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(
            r,
            expected_length=existing_assignments,
            resource_url=collection_url)
        self.assertRoleAssignmentNotInListResponse(r, gd_entity)
        self.assertRoleAssignmentNotInListResponse(r, ud_entity)
        self.assertRoleAssignmentNotInListResponse(r, gp_entity)
        self.assertRoleAssignmentNotInListResponse(r, up_entity)

    def test_get_effective_role_assignments(self):
        """Call ``GET /role_assignments?effective``.

        Test Plan:

        - Create two extra user for tests
        - Add these users to a group
        - Add a role assignment for the group on a domain
        - Get a list of all role assignments, checking one has been added
        - Then get a list of all effective role assignments - the group
          assignment should have turned into assignments on the domain
          for each of the group members.

        """
        self.user1 = self.new_user_ref(
            domain_id=self.domain['id'])
        password = self.user1['password']
        self.user1 = self.identity_api.create_user(self.user1)
        self.user1['password'] = password
        self.user2 = self.new_user_ref(
            domain_id=self.domain['id'])
        password = self.user2['password']
        self.user2 = self.identity_api.create_user(self.user2)
        self.user2['password'] = password
        self.identity_api.add_user_to_group(self.user1['id'], self.group['id'])
        self.identity_api.add_user_to_group(self.user2['id'], self.group['id'])

        collection_url = '/role_assignments'
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r,
                                                   resource_url=collection_url)
        existing_assignments = len(r.result.get('role_assignments'))

        gd_url, gd_entity = _build_role_assignment_url_and_entity(
            domain_id=self.domain_id, group_id=self.group_id,
            role_id=self.role_id)
        self.put(gd_url)
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(
            r,
            expected_length=existing_assignments + 1,
            resource_url=collection_url)
        self.assertRoleAssignmentInListResponse(r, gd_entity, link_url=gd_url)

        # Now re-read the collection asking for effective roles - this
        # should mean the group assignment is translated into the two
        # member user assignments
        collection_url = '/role_assignments?effective'
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(
            r,
            expected_length=existing_assignments + 2,
            resource_url=collection_url)
        unused, ud_entity = _build_role_assignment_url_and_entity(
            domain_id=self.domain_id, user_id=self.user1['id'],
            role_id=self.role_id)
        gd_url, unused = _build_role_assignment_url_and_entity(
            domain_id=self.domain_id, group_id=self.group['id'],
            role_id=self.role_id)
        self.assertRoleAssignmentInListResponse(r, ud_entity, link_url=gd_url)
        ud_url, ud_entity = _build_role_assignment_url_and_entity(
            domain_id=self.domain_id, user_id=self.user2['id'],
            role_id=self.role_id)
        self.assertRoleAssignmentInListResponse(r, ud_entity, link_url=gd_url)

    def test_check_effective_values_for_role_assignments(self):
        """Call ``GET /role_assignments?effective=value``.

        Check the various ways of specifying the 'effective'
        query parameter.  If the 'effective' query parameter
        is included then this should always be treated as meaning 'True'
        unless it is specified as:

        {url}?effective=0

        This is by design to match the agreed way of handling
        policy checking on query/filter parameters.

        Test Plan:

        - Create two extra user for tests
        - Add these users to a group
        - Add a role assignment for the group on a domain
        - Get a list of all role assignments, checking one has been added
        - Then issue various request with different ways of defining
          the 'effective' query parameter. As we have tested the
          correctness of the data coming back when we get effective roles
          in other tests, here we just use the count of entities to
          know if we are getting effective roles or not

        """
        self.user1 = self.new_user_ref(
            domain_id=self.domain['id'])
        password = self.user1['password']
        self.user1 = self.identity_api.create_user(self.user1)
        self.user1['password'] = password
        self.user2 = self.new_user_ref(
            domain_id=self.domain['id'])
        password = self.user2['password']
        self.user2 = self.identity_api.create_user(self.user2)
        self.user2['password'] = password
        self.identity_api.add_user_to_group(self.user1['id'], self.group['id'])
        self.identity_api.add_user_to_group(self.user2['id'], self.group['id'])

        collection_url = '/role_assignments'
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r,
                                                   resource_url=collection_url)
        existing_assignments = len(r.result.get('role_assignments'))

        gd_url, gd_entity = _build_role_assignment_url_and_entity(
            domain_id=self.domain_id, group_id=self.group_id,
            role_id=self.role_id)
        self.put(gd_url)
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(
            r,
            expected_length=existing_assignments + 1,
            resource_url=collection_url)
        self.assertRoleAssignmentInListResponse(r, gd_entity, link_url=gd_url)

        # Now re-read the collection asking for effective roles,
        # using the most common way of defining "effective'. This
        # should mean the group assignment is translated into the two
        # member user assignments
        collection_url = '/role_assignments?effective'
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(
            r,
            expected_length=existing_assignments + 2,
            resource_url=collection_url)
        # Now set 'effective' to false explicitly - should get
        # back the regular roles
        collection_url = '/role_assignments?effective=0'
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(
            r,
            expected_length=existing_assignments + 1,
            resource_url=collection_url)
        # Now try setting  'effective' to 'False' explicitly- this is
        # NOT supported as a way of setting a query or filter
        # parameter to false by design. Hence we should get back
        # effective roles.
        collection_url = '/role_assignments?effective=False'
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(
            r,
            expected_length=existing_assignments + 2,
            resource_url=collection_url)
        # Now set 'effective' to True explicitly
        collection_url = '/role_assignments?effective=True'
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(
            r,
            expected_length=existing_assignments + 2,
            resource_url=collection_url)

    def test_filtered_role_assignments(self):
        """Call ``GET /role_assignments?filters``.

        Test Plan:

        - Create extra users, group, role and project for tests
        - Make the following assignments:
          Give group1, role1 on project1 and domain
          Give user1, role2 on project1 and domain
          Make User1 a member of Group1
        - Test a series of single filter list calls, checking that
          the correct results are obtained
        - Test a multi-filtered list call
        - Test listing all effective roles for a given user
        - Test the equivalent of the list of roles in a project scoped
          token (all effective roles for a user on a project)

        """

        # Since the default fixtures already assign some roles to the
        # user it creates, we also need a new user that will not have any
        # existing assignments
        self.user1 = self.new_user_ref(
            domain_id=self.domain['id'])
        password = self.user1['password']
        self.user1 = self.identity_api.create_user(self.user1)
        self.user1['password'] = password
        self.user2 = self.new_user_ref(
            domain_id=self.domain['id'])
        password = self.user2['password']
        self.user2 = self.identity_api.create_user(self.user2)
        self.user2['password'] = password
        self.group1 = self.new_group_ref(
            domain_id=self.domain['id'])
        self.group1 = self.identity_api.create_group(self.group1)
        self.identity_api.add_user_to_group(self.user1['id'],
                                            self.group1['id'])
        self.identity_api.add_user_to_group(self.user2['id'],
                                            self.group1['id'])
        self.project1 = self.new_project_ref(
            domain_id=self.domain['id'])
        self.resource_api.create_project(self.project1['id'], self.project1)
        self.role1 = self.new_role_ref()
        self.role_api.create_role(self.role1['id'], self.role1)
        self.role2 = self.new_role_ref()
        self.role_api.create_role(self.role2['id'], self.role2)

        # Now add one of each of the four types of assignment

        gd_url, gd_entity = _build_role_assignment_url_and_entity(
            domain_id=self.domain_id, group_id=self.group1['id'],
            role_id=self.role1['id'])
        self.put(gd_url)

        ud_url, ud_entity = _build_role_assignment_url_and_entity(
            domain_id=self.domain_id, user_id=self.user1['id'],
            role_id=self.role2['id'])
        self.put(ud_url)

        gp_url, gp_entity = _build_role_assignment_url_and_entity(
            project_id=self.project1['id'], group_id=self.group1['id'],
            role_id=self.role1['id'])
        self.put(gp_url)

        up_url, up_entity = _build_role_assignment_url_and_entity(
            project_id=self.project1['id'], user_id=self.user1['id'],
            role_id=self.role2['id'])
        self.put(up_url)

        # Now list by various filters to make sure we get back the right ones

        collection_url = ('/role_assignments?scope.project.id=%s' %
                          self.project1['id'])
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r,
                                                   expected_length=2,
                                                   resource_url=collection_url)
        self.assertRoleAssignmentInListResponse(r, up_entity, link_url=up_url)
        self.assertRoleAssignmentInListResponse(r, gp_entity, link_url=gp_url)

        collection_url = ('/role_assignments?scope.domain.id=%s' %
                          self.domain['id'])
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r,
                                                   expected_length=2,
                                                   resource_url=collection_url)
        self.assertRoleAssignmentInListResponse(r, ud_entity, link_url=ud_url)
        self.assertRoleAssignmentInListResponse(r, gd_entity, link_url=gd_url)

        collection_url = '/role_assignments?user.id=%s' % self.user1['id']
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r,
                                                   expected_length=2,
                                                   resource_url=collection_url)
        self.assertRoleAssignmentInListResponse(r, up_entity, link_url=up_url)
        self.assertRoleAssignmentInListResponse(r, ud_entity, link_url=ud_url)

        collection_url = '/role_assignments?group.id=%s' % self.group1['id']
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r,
                                                   expected_length=2,
                                                   resource_url=collection_url)
        self.assertRoleAssignmentInListResponse(r, gd_entity, link_url=gd_url)
        self.assertRoleAssignmentInListResponse(r, gp_entity, link_url=gp_url)

        collection_url = '/role_assignments?role.id=%s' % self.role1['id']
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r,
                                                   expected_length=2,
                                                   resource_url=collection_url)
        self.assertRoleAssignmentInListResponse(r, gd_entity, link_url=gd_url)
        self.assertRoleAssignmentInListResponse(r, gp_entity, link_url=gp_url)

        # Let's try combining two filers together....

        collection_url = (
            '/role_assignments?user.id=%(user_id)s'
            '&scope.project.id=%(project_id)s' % {
                'user_id': self.user1['id'],
                'project_id': self.project1['id']})
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r,
                                                   expected_length=1,
                                                   resource_url=collection_url)
        self.assertRoleAssignmentInListResponse(r, up_entity, link_url=up_url)

        # Now for a harder one - filter for user with effective
        # roles - this should return role assignment that were directly
        # assigned as well as by virtue of group membership

        collection_url = ('/role_assignments?effective&user.id=%s' %
                          self.user1['id'])
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r,
                                                   expected_length=4,
                                                   resource_url=collection_url)
        # Should have the two direct roles...
        self.assertRoleAssignmentInListResponse(r, up_entity, link_url=up_url)
        self.assertRoleAssignmentInListResponse(r, ud_entity, link_url=ud_url)
        # ...and the two via group membership...
        unused, up1_entity = _build_role_assignment_url_and_entity(
            project_id=self.project1['id'], user_id=self.user1['id'],
            role_id=self.role1['id'])
        unused, ud1_entity = _build_role_assignment_url_and_entity(
            domain_id=self.domain_id, user_id=self.user1['id'],
            role_id=self.role1['id'])
        gp1_url, unused = _build_role_assignment_url_and_entity(
            project_id=self.project1['id'], group_id=self.group1['id'],
            role_id=self.role1['id'])
        gd1_url, unused = _build_role_assignment_url_and_entity(
            domain_id=self.domain_id, group_id=self.group1['id'],
            role_id=self.role1['id'])
        self.assertRoleAssignmentInListResponse(r, up1_entity,
                                                link_url=gp1_url)
        self.assertRoleAssignmentInListResponse(r, ud1_entity,
                                                link_url=gd1_url)

        # ...and for the grand-daddy of them all, simulate the request
        # that would generate the list of effective roles in a project
        # scoped token.

        collection_url = (
            '/role_assignments?effective&user.id=%(user_id)s'
            '&scope.project.id=%(project_id)s' % {
                'user_id': self.user1['id'],
                'project_id': self.project1['id']})
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r,
                                                   expected_length=2,
                                                   resource_url=collection_url)
        # Should have one direct role and one from group membership...
        self.assertRoleAssignmentInListResponse(r, up_entity, link_url=up_url)
        self.assertRoleAssignmentInListResponse(r, up1_entity,
                                                link_url=gp1_url)


class AssignmentInheritanceTestCase(test_v3.RestfulTestCase):
    """Test inheritance crud and its effects."""

    def config_overrides(self):
        super(AssignmentInheritanceTestCase, self).config_overrides()
        self.config_fixture.config(group='os_inherit', enabled=True)

    def test_get_token_from_inherited_user_domain_role_grants(self):
        # Create a new user to ensure that no grant is loaded from sample data
        user = self.new_user_ref(domain_id=self.domain_id)
        password = user['password']
        user = self.identity_api.create_user(user)
        user['password'] = password

        # Define domain and project authentication data
        domain_auth_data = self.build_authentication_request(
            user_id=user['id'],
            password=user['password'],
            domain_id=self.domain_id)
        project_auth_data = self.build_authentication_request(
            user_id=user['id'],
            password=user['password'],
            project_id=self.project_id)

        # Check the user cannot get a domain nor a project token
        self.v3_authenticate_token(domain_auth_data, expected_status=401)
        self.v3_authenticate_token(project_auth_data, expected_status=401)

        # Grant non-inherited role for user on domain
        non_inher_ud_url, non_inher_ud_entity = (
            _build_role_assignment_url_and_entity(domain_id=self.domain_id,
                                                  user_id=user['id'],
                                                  role_id=self.role_id))
        self.put(non_inher_ud_url)

        # Check the user can get only a domain token
        self.v3_authenticate_token(domain_auth_data)
        self.v3_authenticate_token(project_auth_data, expected_status=401)

        # Create inherited role
        inherited_role = {'id': uuid.uuid4().hex, 'name': 'inherited'}
        self.role_api.create_role(inherited_role['id'], inherited_role)

        # Grant inherited role for user on domain
        inher_ud_url, inher_ud_entity = _build_role_assignment_url_and_entity(
            domain_id=self.domain_id, user_id=user['id'],
            role_id=inherited_role['id'], inherited_to_projects=True)
        self.put(inher_ud_url)

        # Check the user can get both a domain and a project token
        self.v3_authenticate_token(domain_auth_data)
        self.v3_authenticate_token(project_auth_data)

        # Delete inherited grant
        self.delete(inher_ud_url)

        # Check the user can only get a domain token
        self.v3_authenticate_token(domain_auth_data)
        self.v3_authenticate_token(project_auth_data, expected_status=401)

        # Delete non-inherited grant
        self.delete(non_inher_ud_url)

        # Check the user cannot get a domain token anymore
        self.v3_authenticate_token(domain_auth_data, expected_status=401)

    def test_get_token_from_inherited_group_domain_role_grants(self):
        # Create a new group and put a new user in it to
        # ensure that no grant is loaded from sample data
        user = self.new_user_ref(domain_id=self.domain_id)
        password = user['password']
        user = self.identity_api.create_user(user)
        user['password'] = password

        group = self.new_group_ref(domain_id=self.domain['id'])
        group = self.identity_api.create_group(group)
        self.identity_api.add_user_to_group(user['id'], group['id'])

        # Define domain and project authentication data
        domain_auth_data = self.build_authentication_request(
            user_id=user['id'],
            password=user['password'],
            domain_id=self.domain_id)
        project_auth_data = self.build_authentication_request(
            user_id=user['id'],
            password=user['password'],
            project_id=self.project_id)

        # Check the user cannot get a domain nor a project token
        self.v3_authenticate_token(domain_auth_data, expected_status=401)
        self.v3_authenticate_token(project_auth_data, expected_status=401)

        # Grant non-inherited role for user on domain
        non_inher_gd_url, non_inher_gd_entity = (
            _build_role_assignment_url_and_entity(domain_id=self.domain_id,
                                                  user_id=user['id'],
                                                  role_id=self.role_id))
        self.put(non_inher_gd_url)

        # Check the user can get only a domain token
        self.v3_authenticate_token(domain_auth_data)
        self.v3_authenticate_token(project_auth_data, expected_status=401)

        # Create inherited role
        inherited_role = {'id': uuid.uuid4().hex, 'name': 'inherited'}
        self.role_api.create_role(inherited_role['id'], inherited_role)

        # Grant inherited role for user on domain
        inher_gd_url, inher_gd_entity = _build_role_assignment_url_and_entity(
            domain_id=self.domain_id, user_id=user['id'],
            role_id=inherited_role['id'], inherited_to_projects=True)
        self.put(inher_gd_url)

        # Check the user can get both a domain and a project token
        self.v3_authenticate_token(domain_auth_data)
        self.v3_authenticate_token(project_auth_data)

        # Delete inherited grant
        self.delete(inher_gd_url)

        # Check the user can only get a domain token
        self.v3_authenticate_token(domain_auth_data)
        self.v3_authenticate_token(project_auth_data, expected_status=401)

        # Delete non-inherited grant
        self.delete(non_inher_gd_url)

        # Check the user cannot get a domain token anymore
        self.v3_authenticate_token(domain_auth_data, expected_status=401)

    def test_crud_user_inherited_domain_role_grants(self):
        role_list = []
        for _ in range(2):
            role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
            self.role_api.create_role(role['id'], role)
            role_list.append(role)

        # Create a non-inherited role as a spoiler
        self.assignment_api.create_grant(
            role_list[1]['id'], user_id=self.user['id'],
            domain_id=self.domain_id)

        base_collection_url = (
            '/OS-INHERIT/domains/%(domain_id)s/users/%(user_id)s/roles' % {
                'domain_id': self.domain_id,
                'user_id': self.user['id']})
        member_url = '%(collection_url)s/%(role_id)s/inherited_to_projects' % {
            'collection_url': base_collection_url,
            'role_id': role_list[0]['id']}
        collection_url = base_collection_url + '/inherited_to_projects'

        self.put(member_url)

        # Check we can read it back
        self.head(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, ref=role_list[0],
                                         resource_url=collection_url)

        # Now delete and check its gone
        self.delete(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, expected_length=0,
                                         resource_url=collection_url)

    def test_list_role_assignments_for_inherited_domain_grants(self):
        """Call ``GET /role_assignments with inherited domain grants``.

        Test Plan:

        - Create 4 roles
        - Create a domain with a user and two projects
        - Assign two direct roles to project1
        - Assign a spoiler role to project2
        - Issue the URL to add inherited role to the domain
        - Issue the URL to check it is indeed on the domain
        - Issue the URL to check effective roles on project1 - this
          should return 3 roles.

        """
        role_list = []
        for _ in range(4):
            role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
            self.role_api.create_role(role['id'], role)
            role_list.append(role)

        domain = self.new_domain_ref()
        self.resource_api.create_domain(domain['id'], domain)
        user1 = self.new_user_ref(
            domain_id=domain['id'])
        password = user1['password']
        user1 = self.identity_api.create_user(user1)
        user1['password'] = password
        project1 = self.new_project_ref(
            domain_id=domain['id'])
        self.resource_api.create_project(project1['id'], project1)
        project2 = self.new_project_ref(
            domain_id=domain['id'])
        self.resource_api.create_project(project2['id'], project2)
        # Add some roles to the project
        self.assignment_api.add_role_to_user_and_project(
            user1['id'], project1['id'], role_list[0]['id'])
        self.assignment_api.add_role_to_user_and_project(
            user1['id'], project1['id'], role_list[1]['id'])
        # ..and one on a different project as a spoiler
        self.assignment_api.add_role_to_user_and_project(
            user1['id'], project2['id'], role_list[2]['id'])

        # Now create our inherited role on the domain
        base_collection_url = (
            '/OS-INHERIT/domains/%(domain_id)s/users/%(user_id)s/roles' % {
                'domain_id': domain['id'],
                'user_id': user1['id']})
        member_url = '%(collection_url)s/%(role_id)s/inherited_to_projects' % {
            'collection_url': base_collection_url,
            'role_id': role_list[3]['id']}
        collection_url = base_collection_url + '/inherited_to_projects'

        self.put(member_url)
        self.head(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, ref=role_list[3],
                                         resource_url=collection_url)

        # Now use the list domain role assignments api to check if this
        # is included
        collection_url = (
            '/role_assignments?user.id=%(user_id)s'
            '&scope.domain.id=%(domain_id)s' % {
                'user_id': user1['id'],
                'domain_id': domain['id']})
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r,
                                                   expected_length=1,
                                                   resource_url=collection_url)
        ud_url, ud_entity = _build_role_assignment_url_and_entity(
            domain_id=domain['id'], user_id=user1['id'],
            role_id=role_list[3]['id'], inherited_to_projects=True)
        self.assertRoleAssignmentInListResponse(r, ud_entity, link_url=ud_url)

        # Now ask for effective list role assignments - the role should
        # turn into a project role, along with the two direct roles that are
        # on the project
        collection_url = (
            '/role_assignments?effective&user.id=%(user_id)s'
            '&scope.project.id=%(project_id)s' % {
                'user_id': user1['id'],
                'project_id': project1['id']})
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r,
                                                   expected_length=3,
                                                   resource_url=collection_url)
        # An effective role for an inherited role will be a project
        # entity, with a domain link to the inherited assignment
        unused, up_entity = _build_role_assignment_url_and_entity(
            project_id=project1['id'], user_id=user1['id'],
            role_id=role_list[3]['id'])
        ud_url, unused = _build_role_assignment_url_and_entity(
            domain_id=domain['id'], user_id=user1['id'],
            role_id=role_list[3]['id'], inherited_to_projects=True)
        self.assertRoleAssignmentInListResponse(r, up_entity, link_url=ud_url)

    def test_list_role_assignments_for_disabled_inheritance_extension(self):
        """Call ``GET /role_assignments with inherited domain grants``.

        Test Plan:

        - Issue the URL to add inherited role to the domain
        - Issue the URL to check effective roles on project include the
          inherited role
        - Disable the extension
        - Re-check the effective roles, proving the inherited role no longer
          shows up.

        """

        role_list = []
        for _ in range(4):
            role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
            self.role_api.create_role(role['id'], role)
            role_list.append(role)

        domain = self.new_domain_ref()
        self.resource_api.create_domain(domain['id'], domain)
        user1 = self.new_user_ref(
            domain_id=domain['id'])
        password = user1['password']
        user1 = self.identity_api.create_user(user1)
        user1['password'] = password
        project1 = self.new_project_ref(
            domain_id=domain['id'])
        self.resource_api.create_project(project1['id'], project1)
        project2 = self.new_project_ref(
            domain_id=domain['id'])
        self.resource_api.create_project(project2['id'], project2)
        # Add some roles to the project
        self.assignment_api.add_role_to_user_and_project(
            user1['id'], project1['id'], role_list[0]['id'])
        self.assignment_api.add_role_to_user_and_project(
            user1['id'], project1['id'], role_list[1]['id'])
        # ..and one on a different project as a spoiler
        self.assignment_api.add_role_to_user_and_project(
            user1['id'], project2['id'], role_list[2]['id'])

        # Now create our inherited role on the domain
        base_collection_url = (
            '/OS-INHERIT/domains/%(domain_id)s/users/%(user_id)s/roles' % {
                'domain_id': domain['id'],
                'user_id': user1['id']})
        member_url = '%(collection_url)s/%(role_id)s/inherited_to_projects' % {
            'collection_url': base_collection_url,
            'role_id': role_list[3]['id']}
        collection_url = base_collection_url + '/inherited_to_projects'

        self.put(member_url)
        self.head(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, ref=role_list[3],
                                         resource_url=collection_url)

        # Get effective list role assignments - the role should
        # turn into a project role, along with the two direct roles that are
        # on the project
        collection_url = (
            '/role_assignments?effective&user.id=%(user_id)s'
            '&scope.project.id=%(project_id)s' % {
                'user_id': user1['id'],
                'project_id': project1['id']})
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r,
                                                   expected_length=3,
                                                   resource_url=collection_url)

        unused, up_entity = _build_role_assignment_url_and_entity(
            project_id=project1['id'], user_id=user1['id'],
            role_id=role_list[3]['id'])
        ud_url, unused = _build_role_assignment_url_and_entity(
            domain_id=domain['id'], user_id=user1['id'],
            role_id=role_list[3]['id'], inherited_to_projects=True)
        self.assertRoleAssignmentInListResponse(r, up_entity, link_url=ud_url)

        # Disable the extension and re-check the list, the role inherited
        # from the project should no longer show up
        self.config_fixture.config(group='os_inherit', enabled=False)
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r,
                                                   expected_length=2,
                                                   resource_url=collection_url)

        unused, up_entity = _build_role_assignment_url_and_entity(
            project_id=project1['id'], user_id=user1['id'],
            role_id=role_list[3]['id'])
        ud_url, unused = _build_role_assignment_url_and_entity(
            domain_id=domain['id'], user_id=user1['id'],
            role_id=role_list[3]['id'], inherited_to_projects=True)
        self.assertRoleAssignmentNotInListResponse(r, up_entity,
                                                   link_url=ud_url)

    def test_list_role_assignments_for_inherited_group_domain_grants(self):
        """Call ``GET /role_assignments with inherited group domain grants``.

        Test Plan:

        - Create 4 roles
        - Create a domain with a user and two projects
        - Assign two direct roles to project1
        - Assign a spoiler role to project2
        - Issue the URL to add inherited role to the domain
        - Issue the URL to check it is indeed on the domain
        - Issue the URL to check effective roles on project1 - this
          should return 3 roles.

        """
        role_list = []
        for _ in range(4):
            role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
            self.role_api.create_role(role['id'], role)
            role_list.append(role)

        domain = self.new_domain_ref()
        self.resource_api.create_domain(domain['id'], domain)
        user1 = self.new_user_ref(
            domain_id=domain['id'])
        password = user1['password']
        user1 = self.identity_api.create_user(user1)
        user1['password'] = password
        user2 = self.new_user_ref(
            domain_id=domain['id'])
        password = user2['password']
        user2 = self.identity_api.create_user(user2)
        user2['password'] = password
        group1 = self.new_group_ref(
            domain_id=domain['id'])
        group1 = self.identity_api.create_group(group1)
        self.identity_api.add_user_to_group(user1['id'],
                                            group1['id'])
        self.identity_api.add_user_to_group(user2['id'],
                                            group1['id'])
        project1 = self.new_project_ref(
            domain_id=domain['id'])
        self.resource_api.create_project(project1['id'], project1)
        project2 = self.new_project_ref(
            domain_id=domain['id'])
        self.resource_api.create_project(project2['id'], project2)
        # Add some roles to the project
        self.assignment_api.add_role_to_user_and_project(
            user1['id'], project1['id'], role_list[0]['id'])
        self.assignment_api.add_role_to_user_and_project(
            user1['id'], project1['id'], role_list[1]['id'])
        # ..and one on a different project as a spoiler
        self.assignment_api.add_role_to_user_and_project(
            user1['id'], project2['id'], role_list[2]['id'])

        # Now create our inherited role on the domain
        base_collection_url = (
            '/OS-INHERIT/domains/%(domain_id)s/groups/%(group_id)s/roles' % {
                'domain_id': domain['id'],
                'group_id': group1['id']})
        member_url = '%(collection_url)s/%(role_id)s/inherited_to_projects' % {
            'collection_url': base_collection_url,
            'role_id': role_list[3]['id']}
        collection_url = base_collection_url + '/inherited_to_projects'

        self.put(member_url)
        self.head(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, ref=role_list[3],
                                         resource_url=collection_url)

        # Now use the list domain role assignments api to check if this
        # is included
        collection_url = (
            '/role_assignments?group.id=%(group_id)s'
            '&scope.domain.id=%(domain_id)s' % {
                'group_id': group1['id'],
                'domain_id': domain['id']})
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r,
                                                   expected_length=1,
                                                   resource_url=collection_url)
        gd_url, gd_entity = _build_role_assignment_url_and_entity(
            domain_id=domain['id'], group_id=group1['id'],
            role_id=role_list[3]['id'], inherited_to_projects=True)
        self.assertRoleAssignmentInListResponse(r, gd_entity, link_url=gd_url)

        # Now ask for effective list role assignments - the role should
        # turn into a user project role, along with the two direct roles
        # that are on the project
        collection_url = (
            '/role_assignments?effective&user.id=%(user_id)s'
            '&scope.project.id=%(project_id)s' % {
                'user_id': user1['id'],
                'project_id': project1['id']})
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r,
                                                   expected_length=3,
                                                   resource_url=collection_url)
        # An effective role for an inherited role will be a project
        # entity, with a domain link to the inherited assignment
        unused, up_entity = _build_role_assignment_url_and_entity(
            project_id=project1['id'], user_id=user1['id'],
            role_id=role_list[3]['id'])
        gd_url, unused = _build_role_assignment_url_and_entity(
            domain_id=domain['id'], group_id=group1['id'],
            role_id=role_list[3]['id'], inherited_to_projects=True)
        self.assertRoleAssignmentInListResponse(r, up_entity, link_url=gd_url)

    def test_filtered_role_assignments_for_inherited_grants(self):
        """Call ``GET /role_assignments?scope.OS-INHERIT:inherited_to``.

        Test Plan:

        - Create 5 roles
        - Create a domain with a user, group and two projects
        - Assign three direct spoiler roles to projects
        - Issue the URL to add an inherited user role to the domain
        - Issue the URL to add an inherited group role to the domain
        - Issue the URL to filter by inherited roles - this should
          return just the 2 inherited roles.

        """
        role_list = []
        for _ in range(5):
            role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
            self.role_api.create_role(role['id'], role)
            role_list.append(role)

        domain = self.new_domain_ref()
        self.resource_api.create_domain(domain['id'], domain)
        user1 = self.new_user_ref(
            domain_id=domain['id'])
        password = user1['password']
        user1 = self.identity_api.create_user(user1)
        user1['password'] = password
        group1 = self.new_group_ref(
            domain_id=domain['id'])
        group1 = self.identity_api.create_group(group1)
        project1 = self.new_project_ref(
            domain_id=domain['id'])
        self.resource_api.create_project(project1['id'], project1)
        project2 = self.new_project_ref(
            domain_id=domain['id'])
        self.resource_api.create_project(project2['id'], project2)
        # Add some spoiler roles to the projects
        self.assignment_api.add_role_to_user_and_project(
            user1['id'], project1['id'], role_list[0]['id'])
        self.assignment_api.add_role_to_user_and_project(
            user1['id'], project2['id'], role_list[1]['id'])
        # Create a non-inherited role as a spoiler
        self.assignment_api.create_grant(
            role_list[2]['id'], user_id=user1['id'], domain_id=domain['id'])

        # Now create two inherited roles on the domain, one for a user
        # and one for a domain
        base_collection_url = (
            '/OS-INHERIT/domains/%(domain_id)s/users/%(user_id)s/roles' % {
                'domain_id': domain['id'],
                'user_id': user1['id']})
        member_url = '%(collection_url)s/%(role_id)s/inherited_to_projects' % {
            'collection_url': base_collection_url,
            'role_id': role_list[3]['id']}
        collection_url = base_collection_url + '/inherited_to_projects'

        self.put(member_url)
        self.head(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, ref=role_list[3],
                                         resource_url=collection_url)

        base_collection_url = (
            '/OS-INHERIT/domains/%(domain_id)s/groups/%(group_id)s/roles' % {
                'domain_id': domain['id'],
                'group_id': group1['id']})
        member_url = '%(collection_url)s/%(role_id)s/inherited_to_projects' % {
            'collection_url': base_collection_url,
            'role_id': role_list[4]['id']}
        collection_url = base_collection_url + '/inherited_to_projects'

        self.put(member_url)
        self.head(member_url)
        r = self.get(collection_url)
        self.assertValidRoleListResponse(r, ref=role_list[4],
                                         resource_url=collection_url)

        # Now use the list role assignments api to get a list of inherited
        # roles on the domain - should get back the two roles
        collection_url = (
            '/role_assignments?scope.OS-INHERIT:inherited_to=projects')
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r,
                                                   expected_length=2,
                                                   resource_url=collection_url)
        ud_url, ud_entity = _build_role_assignment_url_and_entity(
            domain_id=domain['id'], user_id=user1['id'],
            role_id=role_list[3]['id'], inherited_to_projects=True)
        gd_url, gd_entity = _build_role_assignment_url_and_entity(
            domain_id=domain['id'], group_id=group1['id'],
            role_id=role_list[4]['id'], inherited_to_projects=True)
        self.assertRoleAssignmentInListResponse(r, ud_entity, link_url=ud_url)
        self.assertRoleAssignmentInListResponse(r, gd_entity, link_url=gd_url)

    def _setup_hierarchical_projects_scenario(self):
        """Creates basic hierarchical projects scenario.

        This basic scenario contains a root with one leaf project and
        two roles with the following names: non-inherited and inherited.

        """
        # Create project hierarchy
        root = self.new_project_ref(domain_id=self.domain['id'])
        leaf = self.new_project_ref(domain_id=self.domain['id'],
                                    parent_id=root['id'])

        self.resource_api.create_project(root['id'], root)
        self.resource_api.create_project(leaf['id'], leaf)

        # Create 'non-inherited' and 'inherited' roles
        non_inherited_role = {'id': uuid.uuid4().hex, 'name': 'non-inherited'}
        self.role_api.create_role(non_inherited_role['id'], non_inherited_role)
        inherited_role = {'id': uuid.uuid4().hex, 'name': 'inherited'}
        self.role_api.create_role(inherited_role['id'], inherited_role)

        return (root['id'], leaf['id'],
                non_inherited_role['id'], inherited_role['id'])

    def test_get_token_from_inherited_user_project_role_grants(self):
        # Create default scenario
        root_id, leaf_id, non_inherited_role_id, inherited_role_id = (
            self._setup_hierarchical_projects_scenario())

        # Define root and leaf projects authentication data
        root_project_auth_data = self.build_authentication_request(
            user_id=self.user['id'],
            password=self.user['password'],
            project_id=root_id)
        leaf_project_auth_data = self.build_authentication_request(
            user_id=self.user['id'],
            password=self.user['password'],
            project_id=leaf_id)

        # Check the user cannot get a token on root nor leaf project
        self.v3_authenticate_token(root_project_auth_data, expected_status=401)
        self.v3_authenticate_token(leaf_project_auth_data, expected_status=401)

        # Grant non-inherited role for user on leaf project
        non_inher_up_url, non_inher_up_entity = (
            _build_role_assignment_url_and_entity(
                project_id=leaf_id, user_id=self.user['id'],
                role_id=non_inherited_role_id))
        self.put(non_inher_up_url)

        # Check the user can only get a token on leaf project
        self.v3_authenticate_token(root_project_auth_data, expected_status=401)
        self.v3_authenticate_token(leaf_project_auth_data)

        # Grant inherited role for user on root project
        inher_up_url, inher_up_entity = _build_role_assignment_url_and_entity(
            project_id=root_id, user_id=self.user['id'],
            role_id=inherited_role_id, inherited_to_projects=True)
        self.put(inher_up_url)

        # Check the user still can get a token only on leaf project
        self.v3_authenticate_token(root_project_auth_data, expected_status=401)
        self.v3_authenticate_token(leaf_project_auth_data)

        # Delete non-inherited grant
        self.delete(non_inher_up_url)

        # Check the inherited role still applies for leaf project
        self.v3_authenticate_token(root_project_auth_data, expected_status=401)
        self.v3_authenticate_token(leaf_project_auth_data)

        # Delete inherited grant
        self.delete(inher_up_url)

        # Check the user cannot get a token on leaf project anymore
        self.v3_authenticate_token(leaf_project_auth_data, expected_status=401)

    def test_get_token_from_inherited_group_project_role_grants(self):
        # Create default scenario
        root_id, leaf_id, non_inherited_role_id, inherited_role_id = (
            self._setup_hierarchical_projects_scenario())

        # Create group and add user to it
        group = self.new_group_ref(domain_id=self.domain['id'])
        group = self.identity_api.create_group(group)
        self.identity_api.add_user_to_group(self.user['id'], group['id'])

        # Define root and leaf projects authentication data
        root_project_auth_data = self.build_authentication_request(
            user_id=self.user['id'],
            password=self.user['password'],
            project_id=root_id)
        leaf_project_auth_data = self.build_authentication_request(
            user_id=self.user['id'],
            password=self.user['password'],
            project_id=leaf_id)

        # Check the user cannot get a token on root nor leaf project
        self.v3_authenticate_token(root_project_auth_data, expected_status=401)
        self.v3_authenticate_token(leaf_project_auth_data, expected_status=401)

        # Grant non-inherited role for group on leaf project
        non_inher_gp_url, non_inher_gp_entity = (
            _build_role_assignment_url_and_entity(
                project_id=leaf_id, group_id=group['id'],
                role_id=non_inherited_role_id))
        self.put(non_inher_gp_url)

        # Check the user can only get a token on leaf project
        self.v3_authenticate_token(root_project_auth_data, expected_status=401)
        self.v3_authenticate_token(leaf_project_auth_data)

        # Grant inherited role for group on root project
        inher_gp_url, inher_gp_entity = _build_role_assignment_url_and_entity(
            project_id=root_id, group_id=group['id'],
            role_id=inherited_role_id, inherited_to_projects=True)
        self.put(inher_gp_url)

        # Check the user still can get a token only on leaf project
        self.v3_authenticate_token(root_project_auth_data, expected_status=401)
        self.v3_authenticate_token(leaf_project_auth_data)

        # Delete no-inherited grant
        self.delete(non_inher_gp_url)

        # Check the inherited role still applies for leaf project
        self.v3_authenticate_token(leaf_project_auth_data)

        # Delete inherited grant
        self.delete(inher_gp_url)

        # Check the user cannot get a token on leaf project anymore
        self.v3_authenticate_token(leaf_project_auth_data, expected_status=401)

    def test_get_role_assignments_for_project_hierarchy(self):
        """Call ``GET /role_assignments``.

        Test Plan:

        - Create 2 roles
        - Create a hierarchy of projects with one root and one leaf project
        - Issue the URL to add a non-inherited user role to the root project
        - Issue the URL to add an inherited user role to the root project
        - Issue the URL to get all role assignments - this should return just
          2 roles (non-inherited and inherited) in the root project.

        """
        # Create default scenario
        root_id, leaf_id, non_inherited_role_id, inherited_role_id = (
            self._setup_hierarchical_projects_scenario())

        # Grant non-inherited role
        non_inher_up_url, non_inher_up_entity = (
            _build_role_assignment_url_and_entity(
                project_id=root_id, user_id=self.user['id'],
                role_id=non_inherited_role_id))
        self.put(non_inher_up_url)

        # Grant inherited role
        inher_up_url, inher_up_entity = _build_role_assignment_url_and_entity(
            project_id=root_id, user_id=self.user['id'],
            role_id=inherited_role_id, inherited_to_projects=True)
        self.put(inher_up_url)

        # Get role assignments
        collection_url = '/role_assignments'
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r,
                                                   resource_url=collection_url)

        # Assert that the user has non-inherited role on root project
        self.assertRoleAssignmentInListResponse(r, non_inher_up_entity,
                                                non_inher_up_url)

        # Assert that the user has inherited role on root project
        self.assertRoleAssignmentInListResponse(r, inher_up_entity,
                                                inher_up_url)

        # Assert that the user does not have non-inherited role on leaf project
        non_inher_up_url = ('/projects/%s/users/%s/roles/%s' %
                            (leaf_id, self.user['id'], non_inherited_role_id))
        non_inher_up_entity['scope']['project']['id'] = leaf_id
        self.assertRoleAssignmentNotInListResponse(r, non_inher_up_entity,
                                                   non_inher_up_url)

        # Assert that the user does not have inherited role on leaf project
        inher_up_entity['scope']['project']['id'] = leaf_id
        self.assertRoleAssignmentNotInListResponse(r, inher_up_entity,
                                                   inher_up_url)

    def test_get_effective_role_assignments_for_project_hierarchy(self):
        """Call ``GET /role_assignments?effective``.

        Test Plan:

        - Create 2 roles
        - Create a hierarchy of projects with one root and one leaf project
        - Issue the URL to add a non-inherited user role to the root project
        - Issue the URL to add an inherited user role to the root project
        - Issue the URL to get effective role assignments - this should return
          1 role (non-inherited) on the root project and 1 role (inherited) on
          the leaf project.

        """
        # Create default scenario
        root_id, leaf_id, non_inherited_role_id, inherited_role_id = (
            self._setup_hierarchical_projects_scenario())

        # Grant non-inherited role
        non_inher_up_url, non_inher_up_entity = (
            _build_role_assignment_url_and_entity(
                project_id=root_id, user_id=self.user['id'],
                role_id=non_inherited_role_id))
        self.put(non_inher_up_url)

        # Grant inherited role
        inher_up_url, inher_up_entity = _build_role_assignment_url_and_entity(
            project_id=root_id, user_id=self.user['id'],
            role_id=inherited_role_id, inherited_to_projects=True)
        self.put(inher_up_url)

        # Get effective role assignments
        collection_url = '/role_assignments?effective'
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r,
                                                   resource_url=collection_url)

        # Assert that the user has non-inherited role on root project
        self.assertRoleAssignmentInListResponse(r, non_inher_up_entity,
                                                non_inher_up_url)

        # Assert that the user does not have inherited role on root project
        self.assertRoleAssignmentNotInListResponse(r, inher_up_entity,
                                                   inher_up_url)

        # Assert that the user does not have non-inherited role on leaf project
        non_inher_up_url = ('/projects/%s/users/%s/roles/%s' %
                            (leaf_id, self.user['id'], non_inherited_role_id))
        non_inher_up_entity['scope']['project']['id'] = leaf_id
        self.assertRoleAssignmentNotInListResponse(r, non_inher_up_entity,
                                                   non_inher_up_url)

        # Assert that the user has inherited role on leaf project
        inher_up_entity['scope']['project']['id'] = leaf_id
        self.assertRoleAssignmentInListResponse(r, inher_up_entity,
                                                inher_up_url)

    def test_get_inherited_role_assignments_for_project_hierarchy(self):
        """Call ``GET /role_assignments?scope.OS-INHERIT:inherited_to``.

        Test Plan:

        - Create 2 roles
        - Create a hierarchy of projects with one root and one leaf project
        - Issue the URL to add a non-inherited user role to the root project
        - Issue the URL to add an inherited user role to the root project
        - Issue the URL to filter inherited to projects role assignments - this
          should return 1 role (inherited) on the root project.

        """
        # Create default scenario
        root_id, leaf_id, non_inherited_role_id, inherited_role_id = (
            self._setup_hierarchical_projects_scenario())

        # Grant non-inherited role
        non_inher_up_url, non_inher_up_entity = (
            _build_role_assignment_url_and_entity(
                project_id=root_id, user_id=self.user['id'],
                role_id=non_inherited_role_id))
        self.put(non_inher_up_url)

        # Grant inherited role
        inher_up_url, inher_up_entity = _build_role_assignment_url_and_entity(
            project_id=root_id, user_id=self.user['id'],
            role_id=inherited_role_id, inherited_to_projects=True)
        self.put(inher_up_url)

        # Get inherited role assignments
        collection_url = ('/role_assignments'
                          '?scope.OS-INHERIT:inherited_to=projects')
        r = self.get(collection_url)
        self.assertValidRoleAssignmentListResponse(r,
                                                   resource_url=collection_url)

        # Assert that the user does not have non-inherited role on root project
        self.assertRoleAssignmentNotInListResponse(r, non_inher_up_entity,
                                                   non_inher_up_url)

        # Assert that the user has inherited role on root project
        self.assertRoleAssignmentInListResponse(r, inher_up_entity,
                                                inher_up_url)

        # Assert that the user does not have non-inherited role on leaf project
        non_inher_up_url = ('/projects/%s/users/%s/roles/%s' %
                            (leaf_id, self.user['id'], non_inherited_role_id))
        non_inher_up_entity['scope']['project']['id'] = leaf_id
        self.assertRoleAssignmentNotInListResponse(r, non_inher_up_entity,
                                                   non_inher_up_url)

        # Assert that the user does not have inherited role on leaf project
        inher_up_entity['scope']['project']['id'] = leaf_id
        self.assertRoleAssignmentNotInListResponse(r, inher_up_entity,
                                                   inher_up_url)


class AssignmentInheritanceDisabledTestCase(test_v3.RestfulTestCase):
    """Test inheritance crud and its effects."""

    def config_overrides(self):
        super(AssignmentInheritanceDisabledTestCase, self).config_overrides()
        self.config_fixture.config(group='os_inherit', enabled=False)

    def test_crud_inherited_role_grants_failed_if_disabled(self):
        role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.role_api.create_role(role['id'], role)

        base_collection_url = (
            '/OS-INHERIT/domains/%(domain_id)s/users/%(user_id)s/roles' % {
                'domain_id': self.domain_id,
                'user_id': self.user['id']})
        member_url = '%(collection_url)s/%(role_id)s/inherited_to_projects' % {
            'collection_url': base_collection_url,
            'role_id': role['id']}
        collection_url = base_collection_url + '/inherited_to_projects'

        self.put(member_url, expected_status=404)
        self.head(member_url, expected_status=404)
        self.get(collection_url, expected_status=404)
        self.delete(member_url, expected_status=404)
