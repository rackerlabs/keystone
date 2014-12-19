# -*- coding: utf-8 -*-
# Copyright 2012 OpenStack Foundation
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

import uuid

from testtools import matchers

from keystone import config
from keystone import exception
from keystone import tests
from keystone.tests.ksfixtures import database
from keystone.tests import test_v3


CONF = config.CONF
DEFAULT_DOMAIN_ID = CONF.identity.default_domain_id


class MyFirstABACSqlTests(tests.SQLDriverOverrides, tests.TestCase):

    def setUp(self):
        super(MyFirstABACSqlTests, self).setUp()
        self.useFixture(database.Database())
        self.load_backends()
        self.setup_test_data()

    def config_files(self):
        config_files = super(MyFirstABACSqlTests, self).config_files()
        config_files.append(tests.dirs.tests_conf('backend_sql.conf'))
        return config_files

    def config_overrides(self):
        super(MyFirstABACSqlTests, self).config_overrides()
        self.config_fixture.config(
            group='assignment',
            driver='keystone.contrib.myfirstabac.backends.sql.ABACAssignment')

    def setup_test_data(self):
        # We don't use the default fixtures (since that relies on being able
        # to add users to projects via the v2 api), but the only thing we do
        # need is the default domain.
        domain = {'description':
                  (u'Owns users and tenants (i.e. projects) '
                   'available on Identity API v2.'),
                  'enabled': True,
                  'id': DEFAULT_DOMAIN_ID,
                  'name': u'Default'}
        try:
            self.resource_api.create_domain(domain['id'], domain)
        except exception.Conflict:
            # When used by RestfulTestCase it may already exist
            pass

        user = {'name': uuid.uuid4().hex,
                'domain_id': DEFAULT_DOMAIN_ID,
                'password': uuid.uuid4().hex}
        self.user = self.identity_api.create_user(user)
        user = {'name': uuid.uuid4().hex,
                'domain_id': DEFAULT_DOMAIN_ID,
                'password': uuid.uuid4().hex}
        self.user1 = self.identity_api.create_user(user)
        project = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                   'domain_id': DEFAULT_DOMAIN_ID}
        self.projectA = (
            self.resource_api.create_project(project['id'], project))
        project = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                   'domain_id': DEFAULT_DOMAIN_ID}
        self.projectB = (
            self.resource_api.create_project(project['id'], project))
        role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.roleA = self.assignment_api.create_role(role['id'], role)
        role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.roleB = self.assignment_api.create_role(role['id'], role)

        self.addCleanup(self.clean_up_test_data)

    def clean_up_test_data(self):
        try:
            self.myfirstabac_api.remove_age_attribute_from_user(
                self.user['id'])
        except exception.UserNotFound:
            pass
        try:
            self.myfirstabac_api.deassign_role_for_18_or_over(
                self.projectA['id'])
        except exception.ProjectNotFound:
            pass
        try:
            self.myfirstabac_api.deassign_role_for_under_18(
                self.projectA['id'])
        except exception.ProjectNotFound:
            pass
        self.assignment_api.delete_role(self.roleA['id'])
        self.assignment_api.delete_role(self.roleB['id'])
        self.resource_api.delete_project(self.projectA['id'])
        self.resource_api.delete_project(self.projectB['id'])
        self.identity_api.delete_user(self.user['id'])

    def test_user_age_attribute(self):
        self.myfirstabac_api.add_age_attribute_to_user(self.user['id'], 18)
        self.assertEqual(
            18,
            self.myfirstabac_api.get_age_attribute_for_user(self.user['id']))
        self.myfirstabac_api.add_age_attribute_to_user(self.user['id'], 17)
        self.assertEqual(
            17,
            self.myfirstabac_api.get_age_attribute_for_user(self.user['id']))
        self.myfirstabac_api.remove_age_attribute_from_user(self.user['id'])
        self.assertIsNone(
            self.myfirstabac_api.get_age_attribute_for_user(self.user['id']))

    def test_project_rules(self):
        # Assign a rule and make sure we get just that one back
        self.myfirstabac_api.assign_role_for_18_or_over(
            self.projectA['id'], self.roleA['id'])
        role_under, role_over = (
            self.myfirstabac_api.get_project_role_rules(self.projectA['id']))
        self.assertEqual(self.roleA['id'], role_over)
        self.assertIsNone(role_under)

        # Assign the second rule and make sure we get both back
        self.myfirstabac_api.assign_role_for_under_18(
            self.projectA['id'], self.roleB['id'])
        role_under, role_over = (
            self.myfirstabac_api.get_project_role_rules(self.projectA['id']))
        self.assertEqual(self.roleA['id'], role_over)
        self.assertEqual(self.roleB['id'], role_under)

        # Remove one rule and make sure we get just the other one back
        self.myfirstabac_api.deassign_role_for_18_or_over(self.projectA['id'])
        role_under, role_over = (
            self.myfirstabac_api.get_project_role_rules(self.projectA['id']))
        self.assertIsNone(role_over)
        self.assertEqual(self.roleB['id'], role_under)

        # Remove the last rule and make sure we get none back
        self.myfirstabac_api.deassign_role_for_under_18(self.projectA['id'])
        role_under, role_over = (
            self.myfirstabac_api.get_project_role_rules(self.projectA['id']))
        self.assertIsNone(role_over)
        self.assertIsNone(role_under)

    def test_get_roles_for_user_and_project(self):
        """Test that the right roles are returned for a project."""

        # No rules defined yet, so user should have no roles
        roles = self.assignment_api.get_roles_for_user_and_project(
            self.user['id'], self.projectA['id'])
        self.assertThat(roles, matchers.HasLength(0))

        # Add rules, but without the user having an age, still no roles
        self.myfirstabac_api.assign_role_for_18_or_over(
            self.projectA['id'], self.roleA['id'])
        self.myfirstabac_api.assign_role_for_under_18(
            self.projectA['id'], self.roleB['id'])
        roles = self.assignment_api.get_roles_for_user_and_project(
            self.user['id'], self.projectA['id'])
        self.assertThat(roles, matchers.HasLength(0))

        # Now give the user an appropriate age that enables the rule
        self.myfirstabac_api.add_age_attribute_to_user(self.user['id'], 18)
        roles = self.assignment_api.get_roles_for_user_and_project(
            self.user['id'], self.projectA['id'])
        self.assertThat(roles, matchers.HasLength(1))
        self.assertThat(roles, matchers.Contains(self.roleA['id']))

        # Making the user younger should change the role returned
        self.myfirstabac_api.add_age_attribute_to_user(self.user['id'], 17)
        roles = self.assignment_api.get_roles_for_user_and_project(
            self.user['id'], self.projectA['id'])
        self.assertThat(roles, matchers.HasLength(1))
        self.assertThat(roles, matchers.Contains(self.roleB['id']))

        # Checking a different project should return no roles
        roles = self.assignment_api.get_roles_for_user_and_project(
            self.user['id'], self.projectB['id'])
        self.assertThat(roles, matchers.HasLength(0))

    def test_list_role_assignments(self):
        # No rules defined yet, so no assignments should be returned
        assignments = self.assignment_api.list_role_assignments()
        self.assertThat(assignments, matchers.HasLength(0))

        # With one user over 18 and one under, with a project that only
        # has an over_18 rule, we should only get back one assignment.
        self.myfirstabac_api.add_age_attribute_to_user(self.user['id'], 18)
        self.myfirstabac_api.add_age_attribute_to_user(self.user1['id'], 17)
        self.myfirstabac_api.assign_role_for_18_or_over(
            self.projectA['id'], self.roleA['id'])
        assignments = self.assignment_api.list_role_assignments()
        self.assertThat(assignments, matchers.HasLength(1))
        self.assertEqual(self.user['id'], assignments[0]['user_id'])
        self.assertEqual(self.projectA['id'], assignments[0]['project_id'])
        self.assertEqual(self.roleA['id'], assignments[0]['role_id'])

        # Adding an under 18 role to ProjectB, should cause it to also
        # be included..
        self.myfirstabac_api.assign_role_for_under_18(
            self.projectB['id'], self.roleB['id'])
        assignments = self.assignment_api.list_role_assignments()
        self.assertThat(assignments, matchers.HasLength(2))
        if assignments[0]['user_id'] == self.user['id']:
            assignmentA = assignments[0]
            assignmentB = assignments[1]
        else:
            assignmentA = assignments[1]
            assignmentB = assignments[0]
        self.assertEqual(self.user['id'], assignmentA['user_id'])
        self.assertEqual(self.projectA['id'], assignmentA['project_id'])
        self.assertEqual(self.roleA['id'], assignmentA['role_id'])
        self.assertEqual(self.user1['id'], assignmentB['user_id'])
        self.assertEqual(self.projectB['id'], assignmentB['project_id'])
        self.assertEqual(self.roleB['id'], assignmentB['role_id'])

    def test_list_user_ids_for_project(self):
        # No rules defined yet, so no users should be returned
        user_ids = self.assignment_api.list_user_ids_for_project(
            self.projectA['id'])
        self.assertThat(user_ids, matchers.HasLength(0))

        # With one user over 18 and one under, with a project that only
        # has an over_18 rule, we should only get back the user who is
        # over 18.
        self.myfirstabac_api.add_age_attribute_to_user(self.user['id'], 18)
        self.myfirstabac_api.add_age_attribute_to_user(self.user1['id'], 17)
        self.myfirstabac_api.assign_role_for_18_or_over(
            self.projectA['id'], self.roleA['id'])
        user_ids = self.assignment_api.list_user_ids_for_project(
            self.projectA['id'])
        self.assertThat(user_ids, matchers.HasLength(1))
        self.assertThat(user_ids, matchers.Contains(self.user['id']))

        # Adding an under 18 rule, should cause both users to be returned.
        self.myfirstabac_api.assign_role_for_under_18(
            self.projectA['id'], self.roleB['id'])
        user_ids = self.assignment_api.list_user_ids_for_project(
            self.projectA['id'])
        self.assertThat(user_ids, matchers.HasLength(2))
        self.assertThat(user_ids, matchers.Contains(self.user['id']))
        self.assertThat(user_ids, matchers.Contains(self.user1['id']))

    def test_list_project_ids_for_user(self):
        # No rules defined yet, so no projects should be returned
        project_ids = self.assignment_api.list_project_ids_for_user(
            self.user['id'], None, None)
        self.assertThat(project_ids, matchers.HasLength(0))
        project_ids = self.assignment_api.list_project_ids_for_user(
            self.user1['id'], None, None)
        self.assertThat(project_ids, matchers.HasLength(0))

        # With a user over 18, we should only get back the project with
        # an over 18 rule.
        self.myfirstabac_api.add_age_attribute_to_user(self.user['id'], 18)
        self.myfirstabac_api.assign_role_for_18_or_over(
            self.projectA['id'], self.roleA['id'])
        self.myfirstabac_api.assign_role_for_under_18(
            self.projectB['id'], self.roleB['id'])
        project_ids = self.assignment_api.list_project_ids_for_user(
            self.user['id'], None, None)
        self.assertThat(project_ids, matchers.HasLength(1))
        self.assertThat(project_ids, matchers.Contains(self.projectA['id']))

        # Adding an over 18 rule to ProjectB should cause it to be
        # returned too.
        self.myfirstabac_api.assign_role_for_18_or_over(
            self.projectB['id'], self.roleB['id'])
        project_ids = self.assignment_api.list_project_ids_for_user(
            self.user['id'], None, None)
        self.assertThat(project_ids, matchers.HasLength(2))
        self.assertThat(project_ids, matchers.Contains(self.projectA['id']))
        self.assertThat(project_ids, matchers.Contains(self.projectB['id']))


class MyFirstABACTest(test_v3.RestfulTestCase, test_v3.AuthTestMixin):

    PATH_PREFIX = 'OS-MY-FIRST-ABAC'
    EXTENSION_NAME = 'myfirstabac'
    EXTENSION_TO_ADD = 'myfirstabac_extension'

    def setUp(self):
        super(MyFirstABACTest, self).setUp()
        self.setup_test_data()

    def setup_test_data(self):
        # Ensure the usual users in RestfulTestCase have roles on the standard
        # projects - the default setup won't do that since it tries to add
        # roles to projects using the old API. We do this by making them over
        # eighteen and assigning a role rule for each of the projects.

        self.myfirstabac_api.add_age_attribute_to_user(self.user_id, 18)
        self.myfirstabac_api.add_age_attribute_to_user(
            self.default_domain_user_id, 18)

        self.myfirstabac_api.assign_role_for_18_or_over(
            self.project_id, self.role_id)
        self.myfirstabac_api.assign_role_for_18_or_over(
            self.default_domain_project_id, self.role_id)
        self.myfirstabac_api.assign_role_for_18_or_over(
            self.project_id, self.role_id)

        # NOTE(henry-nash): Given the above, the fact that we can execute ANY
        # http commands in the tests below show that the users above can
        # successfully authenticate (i.e. are correctly found to have roles on
        # the above projects).

    def config_files(self):
        config_files = super(MyFirstABACTest, self).config_files()
        config_files.append(tests.dirs.tests_conf('backend_sql.conf'))
        return config_files

    def config_overrides(self):
        super(MyFirstABACTest, self).config_overrides()
        self.config_fixture.config(
            group='assignment',
            driver='keystone.contrib.myfirstabac.backends.sql.ABACAssignment')

    def test_user_age_attribute(self):
        user1 = self.new_user_ref(DEFAULT_DOMAIN_ID)
        user1 = self.identity_api.create_user(user1)

        url = ('/users/%(user_id)s/%(prefix)s/age/%(age)s' % {
            'user_id': user1['id'],
            'prefix': self.PATH_PREFIX,
            'age': 18})
        self.put(url, expected_status=204)

        url = ('/users/%(user_id)s/%(prefix)s/age' % {
            'user_id': user1['id'],
            'prefix': self.PATH_PREFIX})
        r = self.get(url, expected_status=200)
        entity = r.result.get('user_attributes')
        self.assertEqual(18, entity['age'])
        self.assertThat(entity, matchers.Contains('links'))

        # Delete the age attribute, and then try and read it back
        url = ('/users/%(user_id)s/%(prefix)s/age' % {
            'user_id': user1['id'],
            'prefix': self.PATH_PREFIX})
        self.delete(url, expected_status=204)
        url = ('/users/%(user_id)s/%(prefix)s/age' % {
            'user_id': user1['id'],
            'prefix': self.PATH_PREFIX})
        self.get(url, expected_status=200)

    def test_project_rules(self):
        project1 = self.new_project_ref(DEFAULT_DOMAIN_ID)
        self.assignment_api.create_project(project1['id'], project1)
        role1 = self.new_role_ref()
        self.assignment_api.create_role(role1['id'], role1)
        role2 = self.new_role_ref()
        self.assignment_api.create_role(role2['id'], role2)

        # Create role rules for a project
        url = ('/projects/%(project_id)s/%(prefix)s'
               '/role_if_18_or_over/%(role_id)s' % {
                   'project_id': project1['id'],
                   'prefix': self.PATH_PREFIX,
                   'role_id': role1['id']})
        self.put(url, expected_status=204)
        url = ('/projects/%(project_id)s/%(prefix)s'
               '/role_if_under_18/%(role_id)s' % {
                   'project_id': project1['id'],
                   'prefix': self.PATH_PREFIX,
                   'role_id': role2['id']})
        self.put(url, expected_status=204)

        # Check we can read them back
        url = ('/projects/%(project_id)s/%(prefix)s'
               '/role_rules' % {
                   'project_id': project1['id'],
                   'prefix': self.PATH_PREFIX})
        r = self.get(url, expected_status=200)
        entity = r.result.get('project_role_rules')
        self.assertEqual(role2['id'], entity['under_18'])
        self.assertEqual(role1['id'], entity['18_and_over'])
        self.assertThat(entity, matchers.Contains('links'))

        # Delete one of them...and check we only get the other back
        url = ('/projects/%(project_id)s/%(prefix)s'
               '/role_if_under_18' % {
                   'project_id': project1['id'],
                   'prefix': self.PATH_PREFIX})
        self.delete(url, expected_status=204)
        url = ('/projects/%(project_id)s/%(prefix)s'
               '/role_rules' % {
                   'project_id': project1['id'],
                   'prefix': self.PATH_PREFIX})
        r = self.get(url, expected_status=200)
        entity = r.result.get('project_role_rules')
        self.assertIsNone(entity['under_18'])
        self.assertEqual(role1['id'], entity['18_and_over'])

        # Delete the other...and make sure we get no rules
        url = ('/projects/%(project_id)s/%(prefix)s'
               '/role_if_18_or_over' % {
                   'project_id': project1['id'],
                   'prefix': self.PATH_PREFIX})
        self.delete(url, expected_status=204)
        url = ('/projects/%(project_id)s/%(prefix)s'
               '/role_rules' % {
                   'project_id': project1['id'],
                   'prefix': self.PATH_PREFIX})
        r = self.get(url, expected_status=200)
        entity = r.result.get('project_role_rules')
        self.assertIsNone(entity['under_18'])
        self.assertIsNone(entity['18_and_over'])

    def test_auth_honors_age_rules(self):
        project1 = self.new_project_ref(DEFAULT_DOMAIN_ID)
        self.assignment_api.create_project(project1['id'], project1)
        role1 = self.new_role_ref()
        self.assignment_api.create_role(role1['id'], role1)
        user1 = self.new_user_ref(DEFAULT_DOMAIN_ID)
        password = user1['password']
        user1 = self.identity_api.create_user(user1)
        user1['password'] = password

        # Create an over 18 rule on a project
        url = ('/projects/%(project_id)s/%(prefix)s'
               '/role_if_18_or_over/%(role_id)s' % {
                   'project_id': project1['id'],
                   'prefix': self.PATH_PREFIX,
                   'role_id': role1['id']})
        self.put(url, expected_status=204)

        # A user over 18 should be able to authenticate
        url = ('/users/%(user_id)s/%(prefix)s/age/%(age)s' % {
               'user_id': user1['id'],
               'prefix': self.PATH_PREFIX,
               'age': 18})
        self.put(url, expected_status=204)
        auth_data = self.build_authentication_request(
            username=user1['name'],
            user_domain_id=DEFAULT_DOMAIN_ID,
            password=user1['password'],
            project_id=project1['id'])
        self.v3_authenticate_token(auth_data)

        # ...but if there are under 18, they have no roles so should not be
        # able to authenticate
        url = ('/users/%(user_id)s/%(prefix)s/age/%(age)s' % {
               'user_id': user1['id'],
               'prefix': self.PATH_PREFIX,
               'age': 17})
        self.put(url, expected_status=204)
        auth_data = self.build_authentication_request(
            username=user1['name'],
            user_domain_id=DEFAULT_DOMAIN_ID,
            password=user1['password'],
            project_id=project1['id'])
        self.v3_authenticate_token(auth_data, expected_status=401)
