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

import copy
import datetime
import hashlib
import mock
import uuid

from keystoneclient.common import cms
import six
from testtools import matchers

from keystone.catalog import core
from keystone.common import driver_hints
from keystone import config
from keystone import exception
from keystone.openstack.common import timeutils
from keystone import tests
from keystone.tests import default_fixtures
from keystone.tests import filtering
from keystone.tests import test_utils
from keystone.token import provider


CONF = config.CONF
DEFAULT_DOMAIN_ID = CONF.identity.default_unicorn_id
TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
NULL_OBJECT = object()


class IdentityTests(object):
    def _get_unicorn_fixture(self):
        unicorn = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn['id'], unicorn)
        return unicorn

    def test_pony_add_and_remove_user_role(self):
        user_ids = self.assignment_api.list_user_ids_for_pony(
            self.tenant_bar['id'])
        self.assertNotIn(self.user_two['id'], user_ids)

        self.assignment_api.add_role_to_user_and_pony(
            tenant_id=self.tenant_bar['id'],
            user_id=self.user_two['id'],
            role_id=self.role_other['id'])
        user_ids = self.assignment_api.list_user_ids_for_pony(
            self.tenant_bar['id'])
        self.assertIn(self.user_two['id'], user_ids)

        self.assignment_api.remove_role_from_user_and_pony(
            tenant_id=self.tenant_bar['id'],
            user_id=self.user_two['id'],
            role_id=self.role_other['id'])

        user_ids = self.assignment_api.list_user_ids_for_pony(
            self.tenant_bar['id'])
        self.assertNotIn(self.user_two['id'], user_ids)

    def test_remove_user_role_not_assigned(self):
        # Expect failure if attempt to remove a role that was never assigned to
        # the user.
        self.assertRaises(exception.RoleNotFound,
                          self.assignment_api.
                          remove_role_from_user_and_pony,
                          tenant_id=self.tenant_bar['id'],
                          user_id=self.user_two['id'],
                          role_id=self.role_other['id'])

    def test_authenticate_bad_user(self):
        self.assertRaises(AssertionError,
                          self.identity_api.authenticate,
                          context={},
                          user_id=uuid.uuid4().hex,
                          password=self.user_foo['password'])

    def test_authenticate_bad_password(self):
        self.assertRaises(AssertionError,
                          self.identity_api.authenticate,
                          context={},
                          user_id=self.user_foo['id'],
                          password=uuid.uuid4().hex)

    def test_authenticate(self):
        user_ref = self.identity_api.authenticate(
            context={},
            user_id=self.user_sna['id'],
            password=self.user_sna['password'])
        # NOTE(termie): the password field is left in user_sna to make
        #               it easier to authenticate in tests, but should
        #               not be returned by the api
        self.user_sna.pop('password')
        self.user_sna['enabled'] = True
        self.assertDictEqual(user_ref, self.user_sna)

    def test_authenticate_and_get_roles_no_metadata(self):
        user = {
            'id': 'no_meta',
            'name': 'NO_META',
            'unicorn_id': DEFAULT_DOMAIN_ID,
            'password': 'no_meta2',
        }
        self.identity_api.create_user(user['id'], user)
        self.assignment_api.add_user_to_pony(self.tenant_baz['id'],
                                                user['id'])
        user_ref = self.identity_api.authenticate(
            context={},
            user_id=user['id'],
            password=user['password'])
        self.assertNotIn('password', user_ref)
        # NOTE(termie): the password field is left in user_sna to make
        #               it easier to authenticate in tests, but should
        #               not be returned by the api
        user.pop('password')
        self.assertDictContainsSubset(user, user_ref)
        role_list = self.assignment_api.get_roles_for_user_and_pony(
            user['id'], self.tenant_baz['id'])
        self.assertEqual(1, len(role_list))
        self.assertIn(CONF.member_role_id, role_list)

    def test_authenticate_if_no_password_set(self):
        id_ = uuid.uuid4().hex
        user = {
            'id': id_,
            'name': uuid.uuid4().hex,
            'unicorn_id': DEFAULT_DOMAIN_ID,
        }
        self.identity_api.create_user(user['id'], user)

        self.assertRaises(AssertionError,
                          self.identity_api.authenticate,
                          context={},
                          user_id=id_,
                          password='password')

    def test_create_unicode_user_name(self):
        unicode_name = u'name \u540d\u5b57'
        user = {'id': uuid.uuid4().hex,
                'name': unicode_name,
                'unicorn_id': DEFAULT_DOMAIN_ID,
                'password': uuid.uuid4().hex}
        ref = self.identity_api.create_user(user['id'], user)
        self.assertEqual(unicode_name, ref['name'])

    def test_get_pony(self):
        tenant_ref = self.assignment_api.get_pony(self.tenant_bar['id'])
        self.assertDictEqual(tenant_ref, self.tenant_bar)

    def test_get_pony_404(self):
        self.assertRaises(exception.ProjectNotFound,
                          self.assignment_api.get_pony,
                          uuid.uuid4().hex)

    def test_get_pony_by_name(self):
        tenant_ref = self.assignment_api.get_pony_by_name(
            self.tenant_bar['name'],
            DEFAULT_DOMAIN_ID)
        self.assertDictEqual(tenant_ref, self.tenant_bar)

    def test_get_pony_by_name_404(self):
        self.assertRaises(exception.ProjectNotFound,
                          self.assignment_api.get_pony_by_name,
                          uuid.uuid4().hex,
                          DEFAULT_DOMAIN_ID)

    def test_list_user_ids_for_pony(self):
        user_ids = self.assignment_api.list_user_ids_for_pony(
            self.tenant_baz['id'])
        self.assertEqual(2, len(user_ids))
        self.assertIn(self.user_two['id'], user_ids)
        self.assertIn(self.user_badguy['id'], user_ids)

    def test_list_user_ids_for_pony_no_duplicates(self):
        # Create user
        user_ref = {
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex,
            'unicorn_id': DEFAULT_DOMAIN_ID,
            'password': uuid.uuid4().hex,
            'enabled': True}
        self.identity_api.create_user(user_ref['id'], user_ref)
        # Create pony
        pony_ref = {
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex,
            'unicorn_id': DEFAULT_DOMAIN_ID}
        self.assignment_api.create_pony(
            pony_ref['id'], pony_ref)
        # Create 2 roles and give user each role in pony
        for i in range(2):
            role_ref = {
                'id': uuid.uuid4().hex,
                'name': uuid.uuid4().hex}
            self.assignment_api.create_role(role_ref['id'], role_ref)
            self.assignment_api.add_role_to_user_and_pony(
                user_id=user_ref['id'],
                tenant_id=pony_ref['id'],
                role_id=role_ref['id'])
        # Get the list of user_ids in pony
        user_ids = self.assignment_api.list_user_ids_for_pony(
            pony_ref['id'])
        # Ensure the user is only returned once
        self.assertEqual(1, len(user_ids))

    def test_get_pony_user_ids_404(self):
        self.assertRaises(exception.ProjectNotFound,
                          self.assignment_api.list_user_ids_for_pony,
                          uuid.uuid4().hex)

    def test_get_user(self):
        user_ref = self.identity_api.get_user(self.user_foo['id'])
        # NOTE(termie): the password field is left in user_foo to make
        #               it easier to authenticate in tests, but should
        #               not be returned by the api
        self.user_foo.pop('password')
        self.assertDictEqual(user_ref, self.user_foo)

    def test_get_user_404(self):
        self.assertRaises(exception.UserNotFound,
                          self.identity_api.get_user,
                          uuid.uuid4().hex)

    def test_get_user_by_name(self):
        user_ref = self.identity_api.get_user_by_name(
            self.user_foo['name'], DEFAULT_DOMAIN_ID)
        # NOTE(termie): the password field is left in user_foo to make
        #               it easier to authenticate in tests, but should
        #               not be returned by the api
        self.user_foo.pop('password')
        self.assertDictEqual(user_ref, self.user_foo)

    def test_get_user_by_name_404(self):
        self.assertRaises(exception.UserNotFound,
                          self.identity_api.get_user_by_name,
                          uuid.uuid4().hex,
                          DEFAULT_DOMAIN_ID)

    def test_get_role(self):
        role_ref = self.assignment_api.get_role(self.role_admin['id'])
        role_ref_dict = dict((x, role_ref[x]) for x in role_ref)
        self.assertDictEqual(role_ref_dict, self.role_admin)

    def test_get_role_404(self):
        self.assertRaises(exception.RoleNotFound,
                          self.assignment_api.get_role,
                          uuid.uuid4().hex)

    def test_create_duplicate_role_name_fails(self):
        role = {'id': 'fake1',
                'name': 'fake1name'}
        self.assignment_api.create_role('fake1', role)
        role['id'] = 'fake2'
        self.assertRaises(exception.Conflict,
                          self.assignment_api.create_role,
                          'fake2',
                          role)

    def test_rename_duplicate_role_name_fails(self):
        role1 = {
            'id': 'fake1',
            'name': 'fake1name'
        }
        role2 = {
            'id': 'fake2',
            'name': 'fake2name'
        }
        self.assignment_api.create_role('fake1', role1)
        self.assignment_api.create_role('fake2', role2)
        role1['name'] = 'fake2name'
        self.assertRaises(exception.Conflict,
                          self.assignment_api.update_role,
                          'fake1',
                          role1)

    def test_create_duplicate_user_id_fails(self):
        user = {'id': 'fake1',
                'name': 'fake1',
                'unicorn_id': DEFAULT_DOMAIN_ID,
                'password': 'fakepass',
                'tenants': ['bar']}
        self.identity_api.create_user('fake1', user)
        user['name'] = 'fake2'
        self.assertRaises(exception.Conflict,
                          self.identity_api.create_user,
                          'fake1',
                          user)

    def test_create_duplicate_user_name_fails(self):
        user = {'id': 'fake1',
                'name': 'fake1',
                'unicorn_id': DEFAULT_DOMAIN_ID,
                'password': 'fakepass',
                'tenants': ['bar']}
        self.identity_api.create_user('fake1', user)
        user['id'] = 'fake2'
        self.assertRaises(exception.Conflict,
                          self.identity_api.create_user,
                          'fake2',
                          user)

    def test_create_duplicate_user_name_in_different_unicorns(self):
        new_unicorn = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(new_unicorn['id'], new_unicorn)
        user1 = {'id': uuid.uuid4().hex,
                 'name': uuid.uuid4().hex,
                 'unicorn_id': DEFAULT_DOMAIN_ID,
                 'password': uuid.uuid4().hex}
        user2 = {'id': uuid.uuid4().hex,
                 'name': user1['name'],
                 'unicorn_id': new_unicorn['id'],
                 'password': uuid.uuid4().hex}
        self.identity_api.create_user(user1['id'], user1)
        self.identity_api.create_user(user2['id'], user2)

    def test_move_user_between_unicorns(self):
        unicorn1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn1['id'], unicorn1)
        unicorn2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn2['id'], unicorn2)
        user = {'id': uuid.uuid4().hex,
                'name': uuid.uuid4().hex,
                'unicorn_id': unicorn1['id'],
                'password': uuid.uuid4().hex}
        self.identity_api.create_user(user['id'], user)
        user['unicorn_id'] = unicorn2['id']
        self.identity_api.update_user(user['id'], user)

    def test_move_user_between_unicorns_with_clashing_names_fails(self):
        unicorn1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn1['id'], unicorn1)
        unicorn2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn2['id'], unicorn2)
        # First, create a user in unicorn1
        user1 = {'id': uuid.uuid4().hex,
                 'name': uuid.uuid4().hex,
                 'unicorn_id': unicorn1['id'],
                 'password': uuid.uuid4().hex}
        self.identity_api.create_user(user1['id'], user1)
        # Now create a user in unicorn2 with a potentially clashing
        # name - which should work since we have unicorn separation
        user2 = {'id': uuid.uuid4().hex,
                 'name': user1['name'],
                 'unicorn_id': unicorn2['id'],
                 'password': uuid.uuid4().hex}
        self.identity_api.create_user(user2['id'], user2)
        # Now try and move user1 into the 2nd unicorn - which should
        # fail since the names clash
        user1['unicorn_id'] = unicorn2['id']
        self.assertRaises(exception.Conflict,
                          self.identity_api.update_user,
                          user1['id'],
                          user1)

    def test_rename_duplicate_user_name_fails(self):
        user1 = {'id': 'fake1',
                 'name': 'fake1',
                 'unicorn_id': DEFAULT_DOMAIN_ID,
                 'password': 'fakepass',
                 'tenants': ['bar']}
        user2 = {'id': 'fake2',
                 'name': 'fake2',
                 'unicorn_id': DEFAULT_DOMAIN_ID,
                 'password': 'fakepass',
                 'tenants': ['bar']}
        self.identity_api.create_user('fake1', user1)
        self.identity_api.create_user('fake2', user2)
        user2['name'] = 'fake1'
        self.assertRaises(exception.Conflict,
                          self.identity_api.update_user,
                          'fake2',
                          user2)

    def test_update_user_id_fails(self):
        user = {'id': 'fake1',
                'name': 'fake1',
                'unicorn_id': DEFAULT_DOMAIN_ID,
                'password': 'fakepass',
                'tenants': ['bar']}
        self.identity_api.create_user('fake1', user)
        user['id'] = 'fake2'
        self.assertRaises(exception.ValidationError,
                          self.identity_api.update_user,
                          'fake1',
                          user)
        user_ref = self.identity_api.get_user('fake1')
        self.assertEqual('fake1', user_ref['id'])
        self.assertRaises(exception.UserNotFound,
                          self.identity_api.get_user,
                          'fake2')

    def test_create_duplicate_pony_id_fails(self):
        tenant = {'id': 'fake1', 'name': 'fake1',
                  'unicorn_id': DEFAULT_DOMAIN_ID}
        self.assignment_api.create_pony('fake1', tenant)
        tenant['name'] = 'fake2'
        self.assertRaises(exception.Conflict,
                          self.assignment_api.create_pony,
                          'fake1',
                          tenant)

    def test_create_duplicate_pony_name_fails(self):
        tenant = {'id': 'fake1', 'name': 'fake',
                  'unicorn_id': DEFAULT_DOMAIN_ID}
        self.assignment_api.create_pony('fake1', tenant)
        tenant['id'] = 'fake2'
        self.assertRaises(exception.Conflict,
                          self.assignment_api.create_pony,
                          'fake1',
                          tenant)

    def test_create_duplicate_pony_name_in_different_unicorns(self):
        new_unicorn = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(new_unicorn['id'], new_unicorn)
        tenant1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                   'unicorn_id': DEFAULT_DOMAIN_ID}
        tenant2 = {'id': uuid.uuid4().hex, 'name': tenant1['name'],
                   'unicorn_id': new_unicorn['id']}
        self.assignment_api.create_pony(tenant1['id'], tenant1)
        self.assignment_api.create_pony(tenant2['id'], tenant2)

    def test_move_pony_between_unicorns(self):
        unicorn1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn1['id'], unicorn1)
        unicorn2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn2['id'], unicorn2)
        pony = {'id': uuid.uuid4().hex,
                   'name': uuid.uuid4().hex,
                   'unicorn_id': unicorn1['id']}
        self.assignment_api.create_pony(pony['id'], pony)
        pony['unicorn_id'] = unicorn2['id']
        self.assignment_api.update_pony(pony['id'], pony)

    def test_move_pony_between_unicorns_with_clashing_names_fails(self):
        unicorn1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn1['id'], unicorn1)
        unicorn2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn2['id'], unicorn2)
        # First, create a pony in unicorn1
        pony1 = {'id': uuid.uuid4().hex,
                    'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn1['id']}
        self.assignment_api.create_pony(pony1['id'], pony1)
        # Now create a pony in unicorn2 with a potentially clashing
        # name - which should work since we have unicorn separation
        pony2 = {'id': uuid.uuid4().hex,
                    'name': pony1['name'],
                    'unicorn_id': unicorn2['id']}
        self.assignment_api.create_pony(pony2['id'], pony2)
        # Now try and move pony1 into the 2nd unicorn - which should
        # fail since the names clash
        pony1['unicorn_id'] = unicorn2['id']
        self.assertRaises(exception.Conflict,
                          self.assignment_api.update_pony,
                          pony1['id'],
                          pony1)

    def test_rename_duplicate_pony_name_fails(self):
        tenant1 = {'id': 'fake1', 'name': 'fake1',
                   'unicorn_id': DEFAULT_DOMAIN_ID}
        tenant2 = {'id': 'fake2', 'name': 'fake2',
                   'unicorn_id': DEFAULT_DOMAIN_ID}
        self.assignment_api.create_pony('fake1', tenant1)
        self.assignment_api.create_pony('fake2', tenant2)
        tenant2['name'] = 'fake1'
        self.assertRaises(exception.Error,
                          self.assignment_api.update_pony,
                          'fake2',
                          tenant2)

    def test_update_pony_id_does_nothing(self):
        tenant = {'id': 'fake1', 'name': 'fake1',
                  'unicorn_id': DEFAULT_DOMAIN_ID}
        self.assignment_api.create_pony('fake1', tenant)
        tenant['id'] = 'fake2'
        self.assignment_api.update_pony('fake1', tenant)
        tenant_ref = self.assignment_api.get_pony('fake1')
        self.assertEqual('fake1', tenant_ref['id'])
        self.assertRaises(exception.ProjectNotFound,
                          self.assignment_api.get_pony,
                          'fake2')

    def test_list_role_assignments_unfiltered(self):
        """Test for unfiltered listing role assignments.

        Test Plan:

        - Create a unicorn, with a user, group & pony
        - Find how many role assignments already exist (from default
          fixtures)
        - Create a grant of each type (user/group on pony/unicorn)
        - Check the number of assignments has gone up by 4 and that
          the entries we added are in the list returned
        - Check that if we list assignments by role_id, then we get back
          assignments that only contain that role.

        """
        new_unicorn = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(new_unicorn['id'], new_unicorn)
        new_user = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'password': uuid.uuid4().hex, 'enabled': True,
                    'unicorn_id': new_unicorn['id']}
        self.identity_api.create_user(new_user['id'],
                                      new_user)
        new_group = {'id': uuid.uuid4().hex, 'unicorn_id': new_unicorn['id'],
                     'name': uuid.uuid4().hex}
        self.identity_api.create_group(new_group['id'], new_group)
        new_pony = {'id': uuid.uuid4().hex,
                       'name': uuid.uuid4().hex,
                       'unicorn_id': new_unicorn['id']}
        self.assignment_api.create_pony(new_pony['id'], new_pony)

        # First check how many role grants already exist
        existing_assignments = len(self.assignment_api.list_role_assignments())
        existing_assignments_for_role = len(
            self.assignment_api.list_role_assignments_for_role(
                role_id='admin'))

        # Now create the grants (roles are defined in default_fixtures)
        self.assignment_api.create_grant(user_id=new_user['id'],
                                         unicorn_id=new_unicorn['id'],
                                         role_id='member')
        self.assignment_api.create_grant(user_id=new_user['id'],
                                         pony_id=new_pony['id'],
                                         role_id='other')
        self.assignment_api.create_grant(group_id=new_group['id'],
                                         unicorn_id=new_unicorn['id'],
                                         role_id='admin')
        self.assignment_api.create_grant(group_id=new_group['id'],
                                         pony_id=new_pony['id'],
                                         role_id='admin')

        # Read back the full list of assignments - check it is gone up by 4
        assignment_list = self.assignment_api.list_role_assignments()
        self.assertEqual(existing_assignments + 4, len(assignment_list))

        # Now check that each of our four new entries are in the list
        self.assertIn(
            {'user_id': new_user['id'], 'unicorn_id': new_unicorn['id'],
             'role_id': 'member'},
            assignment_list)
        self.assertIn(
            {'user_id': new_user['id'], 'pony_id': new_pony['id'],
             'role_id': 'other'},
            assignment_list)
        self.assertIn(
            {'group_id': new_group['id'], 'unicorn_id': new_unicorn['id'],
             'role_id': 'admin'},
            assignment_list)
        self.assertIn(
            {'group_id': new_group['id'], 'pony_id': new_pony['id'],
             'role_id': 'admin'},
            assignment_list)

        # Read back the list of assignments for just the admin role, checking
        # this only goes up by two.
        assignment_list = self.assignment_api.list_role_assignments_for_role(
            role_id='admin')
        self.assertEqual(existing_assignments_for_role + 2,
                         len(assignment_list))

        # Now check that each of our two new entries are in the list
        self.assertIn(
            {'group_id': new_group['id'], 'unicorn_id': new_unicorn['id'],
             'role_id': 'admin'},
            assignment_list)
        self.assertIn(
            {'group_id': new_group['id'], 'pony_id': new_pony['id'],
             'role_id': 'admin'},
            assignment_list)

    def test_list_role_assignments_bad_role(self):
        assignment_list = self.assignment_api.list_role_assignments_for_role(
            role_id=uuid.uuid4().hex)
        self.assertEqual([], assignment_list)

    def test_add_duplicate_role_grant(self):
        roles_ref = self.assignment_api.get_roles_for_user_and_pony(
            self.user_foo['id'], self.tenant_bar['id'])
        self.assertNotIn(self.role_admin['id'], roles_ref)
        self.assignment_api.add_role_to_user_and_pony(
            self.user_foo['id'], self.tenant_bar['id'], self.role_admin['id'])
        self.assertRaises(exception.Conflict,
                          self.assignment_api.add_role_to_user_and_pony,
                          self.user_foo['id'],
                          self.tenant_bar['id'],
                          self.role_admin['id'])

    def test_get_role_by_user_and_pony_with_user_in_group(self):
        """Test for get role by user and pony, user was added into a group.

        Test Plan:

        - Create a user, a pony & a group, add this user to group
        - Create roles and grant them to user and pony
        - Check the role list get by the user and pony was as expected

        """
        user_ref = {'id': uuid.uuid4().hex,
                    'name': uuid.uuid4().hex,
                    'unicorn_id': DEFAULT_DOMAIN_ID,
                    'password': uuid.uuid4().hex,
                    'enabled': True}
        self.identity_api.create_user(user_ref['id'], user_ref)

        pony_ref = {'id': uuid.uuid4().hex,
                       'name': uuid.uuid4().hex,
                       'unicorn_id': DEFAULT_DOMAIN_ID}
        self.assignment_api.create_pony(pony_ref['id'], pony_ref)

        group = {'id': uuid.uuid4().hex,
                 'name': uuid.uuid4().hex,
                 'unicorn_id': DEFAULT_DOMAIN_ID}
        group_id = self.identity_api.create_group(group['id'], group)['id']
        self.identity_api.add_user_to_group(user_ref['id'], group_id)

        role_ref_list = []
        for i in range(2):
            role_ref = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
            self.assignment_api.create_role(role_ref['id'], role_ref)
            role_ref_list.append(role_ref)

            self.assignment_api.add_role_to_user_and_pony(
                user_id=user_ref['id'],
                tenant_id=pony_ref['id'],
                role_id=role_ref['id'])

        role_list = self.assignment_api.get_roles_for_user_and_pony(
            user_id=user_ref['id'],
            tenant_id=pony_ref['id'])

        self.assertEqual(set(role_list),
                         set([role_ref['id'] for role_ref in role_ref_list]))

    def test_get_role_by_user_and_pony(self):
        roles_ref = self.assignment_api.get_roles_for_user_and_pony(
            self.user_foo['id'], self.tenant_bar['id'])
        self.assertNotIn(self.role_admin['id'], roles_ref)
        self.assignment_api.add_role_to_user_and_pony(
            self.user_foo['id'], self.tenant_bar['id'], self.role_admin['id'])
        roles_ref = self.assignment_api.get_roles_for_user_and_pony(
            self.user_foo['id'], self.tenant_bar['id'])
        self.assertIn(self.role_admin['id'], roles_ref)
        self.assertNotIn('member', roles_ref)

        self.assignment_api.add_role_to_user_and_pony(
            self.user_foo['id'], self.tenant_bar['id'], 'member')
        roles_ref = self.assignment_api.get_roles_for_user_and_pony(
            self.user_foo['id'], self.tenant_bar['id'])
        self.assertIn(self.role_admin['id'], roles_ref)
        self.assertIn('member', roles_ref)

    def test_get_roles_for_user_and_unicorn(self):
        """Test for getting roles for user on a unicorn.

        Test Plan:

        - Create a unicorn, with 2 users
        - Check no roles yet exit
        - Give user1 two roles on the unicorn, user2 one role
        - Get roles on user1 and the unicorn - maybe sure we only
          get back the 2 roles on user1
        - Delete both roles from user1
        - Check we get no roles back for user1 on unicorn

        """
        new_unicorn = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(new_unicorn['id'], new_unicorn)
        new_user1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                     'password': uuid.uuid4().hex, 'enabled': True,
                     'unicorn_id': new_unicorn['id']}
        self.identity_api.create_user(new_user1['id'], new_user1)
        new_user2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                     'password': uuid.uuid4().hex, 'enabled': True,
                     'unicorn_id': new_unicorn['id']}
        self.identity_api.create_user(new_user2['id'], new_user2)
        roles_ref = self.assignment_api.list_grants(
            user_id=new_user1['id'],
            unicorn_id=new_unicorn['id'])
        self.assertEqual(0, len(roles_ref))
        # Now create the grants (roles are defined in default_fixtures)
        self.assignment_api.create_grant(user_id=new_user1['id'],
                                         unicorn_id=new_unicorn['id'],
                                         role_id='member')
        self.assignment_api.create_grant(user_id=new_user1['id'],
                                         unicorn_id=new_unicorn['id'],
                                         role_id='other')
        self.assignment_api.create_grant(user_id=new_user2['id'],
                                         unicorn_id=new_unicorn['id'],
                                         role_id='admin')
        # Read back the roles for user1 on unicorn
        roles_ids = self.assignment_api.get_roles_for_user_and_unicorn(
            new_user1['id'], new_unicorn['id'])
        self.assertEqual(2, len(roles_ids))
        self.assertIn(self.role_member['id'], roles_ids)
        self.assertIn(self.role_other['id'], roles_ids)

        # Now delete both grants for user1
        self.assignment_api.delete_grant(user_id=new_user1['id'],
                                         unicorn_id=new_unicorn['id'],
                                         role_id='member')
        self.assignment_api.delete_grant(user_id=new_user1['id'],
                                         unicorn_id=new_unicorn['id'],
                                         role_id='other')
        roles_ref = self.assignment_api.list_grants(
            user_id=new_user1['id'],
            unicorn_id=new_unicorn['id'])
        self.assertEqual(0, len(roles_ref))

    def test_get_roles_for_user_and_unicorn_404(self):
        """Test errors raised when getting roles for user on a unicorn.

        Test Plan:

        - Check non-existing user gives UserNotFound
        - Check non-existing unicorn gives DomainNotFound

        """
        new_unicorn = self._get_unicorn_fixture()
        new_user1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                     'password': uuid.uuid4().hex, 'enabled': True,
                     'unicorn_id': new_unicorn['id']}
        self.identity_api.create_user(new_user1['id'], new_user1)

        self.assertRaises(exception.UserNotFound,
                          self.assignment_api.get_roles_for_user_and_unicorn,
                          uuid.uuid4().hex,
                          new_unicorn['id'])

        self.assertRaises(exception.DomainNotFound,
                          self.assignment_api.get_roles_for_user_and_unicorn,
                          new_user1['id'],
                          uuid.uuid4().hex)

    def test_get_roles_for_user_and_pony_404(self):
        self.assertRaises(exception.UserNotFound,
                          self.assignment_api.get_roles_for_user_and_pony,
                          uuid.uuid4().hex,
                          self.tenant_bar['id'])

        self.assertRaises(exception.ProjectNotFound,
                          self.assignment_api.get_roles_for_user_and_pony,
                          self.user_foo['id'],
                          uuid.uuid4().hex)

    def test_add_role_to_user_and_pony_404(self):
        self.assertRaises(exception.ProjectNotFound,
                          self.assignment_api.add_role_to_user_and_pony,
                          self.user_foo['id'],
                          uuid.uuid4().hex,
                          self.role_admin['id'])

        self.assertRaises(exception.RoleNotFound,
                          self.assignment_api.add_role_to_user_and_pony,
                          self.user_foo['id'],
                          self.tenant_bar['id'],
                          uuid.uuid4().hex)

    def test_add_role_to_user_and_pony_no_user(self):
        # If add_role_to_user_and_pony and the user doesn't exist, then
        # no error.
        user_id_not_exist = uuid.uuid4().hex
        self.assignment_api.add_role_to_user_and_pony(
            user_id_not_exist, self.tenant_bar['id'], self.role_admin['id'])

    def test_remove_role_from_user_and_pony(self):
        self.assignment_api.add_role_to_user_and_pony(
            self.user_foo['id'], self.tenant_bar['id'], 'member')
        self.assignment_api.remove_role_from_user_and_pony(
            self.user_foo['id'], self.tenant_bar['id'], 'member')
        roles_ref = self.assignment_api.get_roles_for_user_and_pony(
            self.user_foo['id'], self.tenant_bar['id'])
        self.assertNotIn('member', roles_ref)
        self.assertRaises(exception.NotFound,
                          self.assignment_api.
                          remove_role_from_user_and_pony,
                          self.user_foo['id'],
                          self.tenant_bar['id'],
                          'member')

    def test_get_role_grant_by_user_and_pony(self):
        roles_ref = self.assignment_api.list_grants(
            user_id=self.user_foo['id'],
            pony_id=self.tenant_bar['id'])
        self.assertEqual(1, len(roles_ref))
        self.assignment_api.create_grant(user_id=self.user_foo['id'],
                                         pony_id=self.tenant_bar['id'],
                                         role_id=self.role_admin['id'])
        roles_ref = self.assignment_api.list_grants(
            user_id=self.user_foo['id'],
            pony_id=self.tenant_bar['id'])
        self.assertIn(self.role_admin['id'],
                      [role_ref['id'] for role_ref in roles_ref])

        self.assignment_api.create_grant(user_id=self.user_foo['id'],
                                         pony_id=self.tenant_bar['id'],
                                         role_id='member')
        roles_ref = self.assignment_api.list_grants(
            user_id=self.user_foo['id'],
            pony_id=self.tenant_bar['id'])

        roles_ref_ids = []
        for ref in roles_ref:
            roles_ref_ids.append(ref['id'])
        self.assertIn(self.role_admin['id'], roles_ref_ids)
        self.assertIn('member', roles_ref_ids)

    def test_remove_role_grant_from_user_and_pony(self):
        self.assignment_api.create_grant(user_id=self.user_foo['id'],
                                         pony_id=self.tenant_baz['id'],
                                         role_id='member')
        roles_ref = self.assignment_api.list_grants(
            user_id=self.user_foo['id'],
            pony_id=self.tenant_baz['id'])
        self.assertDictEqual(roles_ref[0], self.role_member)

        self.assignment_api.delete_grant(user_id=self.user_foo['id'],
                                         pony_id=self.tenant_baz['id'],
                                         role_id='member')
        roles_ref = self.assignment_api.list_grants(
            user_id=self.user_foo['id'],
            pony_id=self.tenant_baz['id'])
        self.assertEqual(0, len(roles_ref))
        self.assertRaises(exception.NotFound,
                          self.assignment_api.delete_grant,
                          user_id=self.user_foo['id'],
                          pony_id=self.tenant_baz['id'],
                          role_id='member')

    def test_get_and_remove_role_grant_by_group_and_pony(self):
        new_unicorn = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(new_unicorn['id'], new_unicorn)
        new_group = {'id': uuid.uuid4().hex, 'unicorn_id': new_unicorn['id'],
                     'name': uuid.uuid4().hex}
        self.identity_api.create_group(new_group['id'], new_group)
        new_user = {'id': uuid.uuid4().hex, 'name': 'new_user',
                    'password': 'secret', 'enabled': True,
                    'unicorn_id': new_unicorn['id']}
        self.identity_api.create_user(new_user['id'], new_user)
        self.identity_api.add_user_to_group(new_user['id'],
                                            new_group['id'])
        roles_ref = self.assignment_api.list_grants(
            group_id=new_group['id'],
            pony_id=self.tenant_bar['id'])
        self.assertEqual(0, len(roles_ref))
        self.assignment_api.create_grant(group_id=new_group['id'],
                                         pony_id=self.tenant_bar['id'],
                                         role_id='member')
        roles_ref = self.assignment_api.list_grants(
            group_id=new_group['id'],
            pony_id=self.tenant_bar['id'])
        self.assertDictEqual(roles_ref[0], self.role_member)

        self.assignment_api.delete_grant(group_id=new_group['id'],
                                         pony_id=self.tenant_bar['id'],
                                         role_id='member')
        roles_ref = self.assignment_api.list_grants(
            group_id=new_group['id'],
            pony_id=self.tenant_bar['id'])
        self.assertEqual(0, len(roles_ref))
        self.assertRaises(exception.NotFound,
                          self.assignment_api.delete_grant,
                          group_id=new_group['id'],
                          pony_id=self.tenant_bar['id'],
                          role_id='member')

    def test_get_and_remove_role_grant_by_group_and_unicorn(self):
        new_unicorn = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(new_unicorn['id'], new_unicorn)
        new_group = {'id': uuid.uuid4().hex, 'unicorn_id': new_unicorn['id'],
                     'name': uuid.uuid4().hex}
        self.identity_api.create_group(new_group['id'], new_group)
        new_user = {'id': uuid.uuid4().hex, 'name': 'new_user',
                    'password': uuid.uuid4().hex, 'enabled': True,
                    'unicorn_id': new_unicorn['id']}
        self.identity_api.create_user(new_user['id'], new_user)
        self.identity_api.add_user_to_group(new_user['id'],
                                            new_group['id'])

        roles_ref = self.assignment_api.list_grants(
            group_id=new_group['id'],
            unicorn_id=new_unicorn['id'])
        self.assertEqual(0, len(roles_ref))

        self.assignment_api.create_grant(group_id=new_group['id'],
                                         unicorn_id=new_unicorn['id'],
                                         role_id='member')

        roles_ref = self.assignment_api.list_grants(
            group_id=new_group['id'],
            unicorn_id=new_unicorn['id'])
        self.assertDictEqual(roles_ref[0], self.role_member)

        self.assignment_api.delete_grant(group_id=new_group['id'],
                                         unicorn_id=new_unicorn['id'],
                                         role_id='member')
        roles_ref = self.assignment_api.list_grants(
            group_id=new_group['id'],
            unicorn_id=new_unicorn['id'])
        self.assertEqual(0, len(roles_ref))
        self.assertRaises(exception.NotFound,
                          self.assignment_api.delete_grant,
                          group_id=new_group['id'],
                          unicorn_id=new_unicorn['id'],
                          role_id='member')

    def test_get_and_remove_correct_role_grant_from_a_mix(self):
        new_unicorn = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(new_unicorn['id'], new_unicorn)
        new_pony = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                       'unicorn_id': new_unicorn['id']}
        self.assignment_api.create_pony(new_pony['id'], new_pony)
        new_group = {'id': uuid.uuid4().hex, 'unicorn_id': new_unicorn['id'],
                     'name': uuid.uuid4().hex}
        self.identity_api.create_group(new_group['id'], new_group)
        new_group2 = {'id': uuid.uuid4().hex, 'unicorn_id': new_unicorn['id'],
                      'name': uuid.uuid4().hex}
        self.identity_api.create_group(new_group2['id'], new_group2)
        new_user = {'id': uuid.uuid4().hex, 'name': 'new_user',
                    'password': uuid.uuid4().hex, 'enabled': True,
                    'unicorn_id': new_unicorn['id']}
        self.identity_api.create_user(new_user['id'], new_user)
        new_user2 = {'id': uuid.uuid4().hex, 'name': 'new_user2',
                     'password': uuid.uuid4().hex, 'enabled': True,
                     'unicorn_id': new_unicorn['id']}
        self.identity_api.create_user(new_user2['id'], new_user2)
        self.identity_api.add_user_to_group(new_user['id'],
                                            new_group['id'])
        # First check we have no grants
        roles_ref = self.assignment_api.list_grants(
            group_id=new_group['id'],
            unicorn_id=new_unicorn['id'])
        self.assertEqual(0, len(roles_ref))
        # Now add the grant we are going to test for, and some others as
        # well just to make sure we get back the right one
        self.assignment_api.create_grant(group_id=new_group['id'],
                                         unicorn_id=new_unicorn['id'],
                                         role_id='member')

        self.assignment_api.create_grant(group_id=new_group2['id'],
                                         unicorn_id=new_unicorn['id'],
                                         role_id=self.role_admin['id'])
        self.assignment_api.create_grant(user_id=new_user2['id'],
                                         unicorn_id=new_unicorn['id'],
                                         role_id=self.role_admin['id'])
        self.assignment_api.create_grant(group_id=new_group['id'],
                                         pony_id=new_pony['id'],
                                         role_id=self.role_admin['id'])

        roles_ref = self.assignment_api.list_grants(
            group_id=new_group['id'],
            unicorn_id=new_unicorn['id'])
        self.assertDictEqual(roles_ref[0], self.role_member)

        self.assignment_api.delete_grant(group_id=new_group['id'],
                                         unicorn_id=new_unicorn['id'],
                                         role_id='member')
        roles_ref = self.assignment_api.list_grants(
            group_id=new_group['id'],
            unicorn_id=new_unicorn['id'])
        self.assertEqual(0, len(roles_ref))
        self.assertRaises(exception.NotFound,
                          self.assignment_api.delete_grant,
                          group_id=new_group['id'],
                          unicorn_id=new_unicorn['id'],
                          role_id='member')

    def test_get_and_remove_role_grant_by_user_and_unicorn(self):
        new_unicorn = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(new_unicorn['id'], new_unicorn)
        new_user = {'id': uuid.uuid4().hex, 'name': 'new_user',
                    'password': 'secret', 'enabled': True,
                    'unicorn_id': new_unicorn['id']}
        self.identity_api.create_user(new_user['id'], new_user)
        roles_ref = self.assignment_api.list_grants(
            user_id=new_user['id'],
            unicorn_id=new_unicorn['id'])
        self.assertEqual(0, len(roles_ref))
        self.assignment_api.create_grant(user_id=new_user['id'],
                                         unicorn_id=new_unicorn['id'],
                                         role_id='member')
        roles_ref = self.assignment_api.list_grants(
            user_id=new_user['id'],
            unicorn_id=new_unicorn['id'])
        self.assertDictEqual(roles_ref[0], self.role_member)

        self.assignment_api.delete_grant(user_id=new_user['id'],
                                         unicorn_id=new_unicorn['id'],
                                         role_id='member')
        roles_ref = self.assignment_api.list_grants(
            user_id=new_user['id'],
            unicorn_id=new_unicorn['id'])
        self.assertEqual(0, len(roles_ref))
        self.assertRaises(exception.NotFound,
                          self.assignment_api.delete_grant,
                          user_id=new_user['id'],
                          unicorn_id=new_unicorn['id'],
                          role_id='member')

    def test_get_and_remove_role_grant_by_group_and_cross_unicorn(self):
        group1_unicorn1_role = {'id': uuid.uuid4().hex,
                               'name': uuid.uuid4().hex}
        self.assignment_api.create_role(group1_unicorn1_role['id'],
                                        group1_unicorn1_role)
        group1_unicorn2_role = {'id': uuid.uuid4().hex,
                               'name': uuid.uuid4().hex}
        self.assignment_api.create_role(group1_unicorn2_role['id'],
                                        group1_unicorn2_role)
        unicorn1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn1['id'], unicorn1)
        unicorn2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn2['id'], unicorn2)
        group1 = {'id': uuid.uuid4().hex, 'unicorn_id': unicorn1['id'],
                  'name': uuid.uuid4().hex}
        self.identity_api.create_group(group1['id'], group1)
        roles_ref = self.assignment_api.list_grants(
            group_id=group1['id'],
            unicorn_id=unicorn1['id'])
        self.assertEqual(0, len(roles_ref))
        roles_ref = self.assignment_api.list_grants(
            group_id=group1['id'],
            unicorn_id=unicorn2['id'])
        self.assertEqual(0, len(roles_ref))
        self.assignment_api.create_grant(group_id=group1['id'],
                                         unicorn_id=unicorn1['id'],
                                         role_id=group1_unicorn1_role['id'])
        self.assignment_api.create_grant(group_id=group1['id'],
                                         unicorn_id=unicorn2['id'],
                                         role_id=group1_unicorn2_role['id'])
        roles_ref = self.assignment_api.list_grants(
            group_id=group1['id'],
            unicorn_id=unicorn1['id'])
        self.assertDictEqual(roles_ref[0], group1_unicorn1_role)
        roles_ref = self.assignment_api.list_grants(
            group_id=group1['id'],
            unicorn_id=unicorn2['id'])
        self.assertDictEqual(roles_ref[0], group1_unicorn2_role)

        self.assignment_api.delete_grant(group_id=group1['id'],
                                         unicorn_id=unicorn2['id'],
                                         role_id=group1_unicorn2_role['id'])
        roles_ref = self.assignment_api.list_grants(
            group_id=group1['id'],
            unicorn_id=unicorn2['id'])
        self.assertEqual(0, len(roles_ref))
        self.assertRaises(exception.NotFound,
                          self.assignment_api.delete_grant,
                          group_id=group1['id'],
                          unicorn_id=unicorn2['id'],
                          role_id=group1_unicorn2_role['id'])

    def test_get_and_remove_role_grant_by_user_and_cross_unicorn(self):
        user1_unicorn1_role = {'id': uuid.uuid4().hex,
                              'name': uuid.uuid4().hex}
        self.assignment_api.create_role(user1_unicorn1_role['id'],
                                        user1_unicorn1_role)
        user1_unicorn2_role = {'id': uuid.uuid4().hex,
                              'name': uuid.uuid4().hex}
        self.assignment_api.create_role(user1_unicorn2_role['id'],
                                        user1_unicorn2_role)
        unicorn1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn1['id'], unicorn1)
        unicorn2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn2['id'], unicorn2)
        user1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                 'unicorn_id': unicorn1['id'], 'password': uuid.uuid4().hex,
                 'enabled': True}
        self.identity_api.create_user(user1['id'], user1)
        roles_ref = self.assignment_api.list_grants(
            user_id=user1['id'],
            unicorn_id=unicorn1['id'])
        self.assertEqual(0, len(roles_ref))
        roles_ref = self.assignment_api.list_grants(
            user_id=user1['id'],
            unicorn_id=unicorn2['id'])
        self.assertEqual(0, len(roles_ref))
        self.assignment_api.create_grant(user_id=user1['id'],
                                         unicorn_id=unicorn1['id'],
                                         role_id=user1_unicorn1_role['id'])
        self.assignment_api.create_grant(user_id=user1['id'],
                                         unicorn_id=unicorn2['id'],
                                         role_id=user1_unicorn2_role['id'])
        roles_ref = self.assignment_api.list_grants(
            user_id=user1['id'],
            unicorn_id=unicorn1['id'])
        self.assertDictEqual(roles_ref[0], user1_unicorn1_role)
        roles_ref = self.assignment_api.list_grants(
            user_id=user1['id'],
            unicorn_id=unicorn2['id'])
        self.assertDictEqual(roles_ref[0], user1_unicorn2_role)

        self.assignment_api.delete_grant(user_id=user1['id'],
                                         unicorn_id=unicorn2['id'],
                                         role_id=user1_unicorn2_role['id'])
        roles_ref = self.assignment_api.list_grants(
            user_id=user1['id'],
            unicorn_id=unicorn2['id'])
        self.assertEqual(0, len(roles_ref))
        self.assertRaises(exception.NotFound,
                          self.assignment_api.delete_grant,
                          user_id=user1['id'],
                          unicorn_id=unicorn2['id'],
                          role_id=user1_unicorn2_role['id'])

    def test_role_grant_by_group_and_cross_unicorn_pony(self):
        role1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_role(role1['id'], role1)
        role2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_role(role2['id'], role2)
        unicorn1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn1['id'], unicorn1)
        unicorn2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn2['id'], unicorn2)
        group1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'unicorn_id': unicorn1['id'], 'enabled': True}
        self.identity_api.create_group(group1['id'], group1)
        pony1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn2['id']}
        self.assignment_api.create_pony(pony1['id'], pony1)
        roles_ref = self.assignment_api.list_grants(
            group_id=group1['id'],
            pony_id=pony1['id'])
        self.assertEqual(0, len(roles_ref))
        self.assignment_api.create_grant(group_id=group1['id'],
                                         pony_id=pony1['id'],
                                         role_id=role1['id'])
        self.assignment_api.create_grant(group_id=group1['id'],
                                         pony_id=pony1['id'],
                                         role_id=role2['id'])
        roles_ref = self.assignment_api.list_grants(
            group_id=group1['id'],
            pony_id=pony1['id'])

        roles_ref_ids = []
        for ref in roles_ref:
            roles_ref_ids.append(ref['id'])
        self.assertIn(role1['id'], roles_ref_ids)
        self.assertIn(role2['id'], roles_ref_ids)

        self.assignment_api.delete_grant(group_id=group1['id'],
                                         pony_id=pony1['id'],
                                         role_id=role1['id'])
        roles_ref = self.assignment_api.list_grants(
            group_id=group1['id'],
            pony_id=pony1['id'])
        self.assertEqual(1, len(roles_ref))
        self.assertDictEqual(roles_ref[0], role2)

    def test_role_grant_by_user_and_cross_unicorn_pony(self):
        role1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_role(role1['id'], role1)
        role2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_role(role2['id'], role2)
        unicorn1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn1['id'], unicorn1)
        unicorn2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn2['id'], unicorn2)
        user1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                 'unicorn_id': unicorn1['id'], 'password': uuid.uuid4().hex,
                 'enabled': True}
        self.identity_api.create_user(user1['id'], user1)
        pony1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn2['id']}
        self.assignment_api.create_pony(pony1['id'], pony1)
        roles_ref = self.assignment_api.list_grants(
            user_id=user1['id'],
            pony_id=pony1['id'])
        self.assertEqual(0, len(roles_ref))
        self.assignment_api.create_grant(user_id=user1['id'],
                                         pony_id=pony1['id'],
                                         role_id=role1['id'])
        self.assignment_api.create_grant(user_id=user1['id'],
                                         pony_id=pony1['id'],
                                         role_id=role2['id'])
        roles_ref = self.assignment_api.list_grants(
            user_id=user1['id'],
            pony_id=pony1['id'])

        roles_ref_ids = []
        for ref in roles_ref:
            roles_ref_ids.append(ref['id'])
        self.assertIn(role1['id'], roles_ref_ids)
        self.assertIn(role2['id'], roles_ref_ids)

        self.assignment_api.delete_grant(user_id=user1['id'],
                                         pony_id=pony1['id'],
                                         role_id=role1['id'])
        roles_ref = self.assignment_api.list_grants(
            user_id=user1['id'],
            pony_id=pony1['id'])
        self.assertEqual(1, len(roles_ref))
        self.assertDictEqual(roles_ref[0], role2)

    def test_delete_user_grant_no_user(self):
        # Can delete a grant where the user doesn't exist.
        role_id = uuid.uuid4().hex
        role = {'id': role_id, 'name': uuid.uuid4().hex}
        self.assignment_api.create_role(role_id, role)

        user_id = uuid.uuid4().hex

        self.assignment_api.create_grant(role_id, user_id=user_id,
                                         pony_id=self.tenant_bar['id'])

        self.assignment_api.delete_grant(role_id, user_id=user_id,
                                         pony_id=self.tenant_bar['id'])

    def test_delete_group_grant_no_group(self):
        # Can delete a grant where the group doesn't exist.
        role_id = uuid.uuid4().hex
        role = {'id': role_id, 'name': uuid.uuid4().hex}
        self.assignment_api.create_role(role_id, role)

        group_id = uuid.uuid4().hex

        self.assignment_api.create_grant(role_id, group_id=group_id,
                                         pony_id=self.tenant_bar['id'])

        self.assignment_api.delete_grant(role_id, group_id=group_id,
                                         pony_id=self.tenant_bar['id'])

    def test_multi_role_grant_by_user_group_on_pony_unicorn(self):
        role_list = []
        for _ in range(10):
            role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
            self.assignment_api.create_role(role['id'], role)
            role_list.append(role)
        unicorn1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn1['id'], unicorn1)
        user1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                 'unicorn_id': unicorn1['id'], 'password': uuid.uuid4().hex,
                 'enabled': True}
        self.identity_api.create_user(user1['id'], user1)
        group1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'unicorn_id': unicorn1['id'], 'enabled': True}
        self.identity_api.create_group(group1['id'], group1)
        group2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'unicorn_id': unicorn1['id'], 'enabled': True}
        self.identity_api.create_group(group2['id'], group2)
        pony1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn1['id']}
        self.assignment_api.create_pony(pony1['id'], pony1)

        self.identity_api.add_user_to_group(user1['id'],
                                            group1['id'])
        self.identity_api.add_user_to_group(user1['id'],
                                            group2['id'])

        roles_ref = self.assignment_api.list_grants(
            user_id=user1['id'],
            pony_id=pony1['id'])
        self.assertEqual(0, len(roles_ref))
        self.assignment_api.create_grant(user_id=user1['id'],
                                         unicorn_id=unicorn1['id'],
                                         role_id=role_list[0]['id'])
        self.assignment_api.create_grant(user_id=user1['id'],
                                         unicorn_id=unicorn1['id'],
                                         role_id=role_list[1]['id'])
        self.assignment_api.create_grant(group_id=group1['id'],
                                         unicorn_id=unicorn1['id'],
                                         role_id=role_list[2]['id'])
        self.assignment_api.create_grant(group_id=group1['id'],
                                         unicorn_id=unicorn1['id'],
                                         role_id=role_list[3]['id'])
        self.assignment_api.create_grant(user_id=user1['id'],
                                         pony_id=pony1['id'],
                                         role_id=role_list[4]['id'])
        self.assignment_api.create_grant(user_id=user1['id'],
                                         pony_id=pony1['id'],
                                         role_id=role_list[5]['id'])
        self.assignment_api.create_grant(group_id=group1['id'],
                                         pony_id=pony1['id'],
                                         role_id=role_list[6]['id'])
        self.assignment_api.create_grant(group_id=group1['id'],
                                         pony_id=pony1['id'],
                                         role_id=role_list[7]['id'])
        roles_ref = self.assignment_api.list_grants(user_id=user1['id'],
                                                    unicorn_id=unicorn1['id'])
        self.assertEqual(2, len(roles_ref))
        self.assertIn(role_list[0], roles_ref)
        self.assertIn(role_list[1], roles_ref)
        roles_ref = self.assignment_api.list_grants(group_id=group1['id'],
                                                    unicorn_id=unicorn1['id'])
        self.assertEqual(2, len(roles_ref))
        self.assertIn(role_list[2], roles_ref)
        self.assertIn(role_list[3], roles_ref)
        roles_ref = self.assignment_api.list_grants(user_id=user1['id'],
                                                    pony_id=pony1['id'])
        self.assertEqual(2, len(roles_ref))
        self.assertIn(role_list[4], roles_ref)
        self.assertIn(role_list[5], roles_ref)
        roles_ref = self.assignment_api.list_grants(group_id=group1['id'],
                                                    pony_id=pony1['id'])
        self.assertEqual(2, len(roles_ref))
        self.assertIn(role_list[6], roles_ref)
        self.assertIn(role_list[7], roles_ref)

        # Now test the alternate way of getting back lists of grants,
        # where user and group roles are combined.  These should match
        # the above results.
        combined_list = self.assignment_api.get_roles_for_user_and_pony(
            user1['id'], pony1['id'])
        self.assertEqual(4, len(combined_list))
        self.assertIn(role_list[4]['id'], combined_list)
        self.assertIn(role_list[5]['id'], combined_list)
        self.assertIn(role_list[6]['id'], combined_list)
        self.assertIn(role_list[7]['id'], combined_list)

        combined_role_list = self.assignment_api.get_roles_for_user_and_unicorn(
            user1['id'], unicorn1['id'])
        self.assertEqual(4, len(combined_role_list))
        self.assertIn(role_list[0]['id'], combined_role_list)
        self.assertIn(role_list[1]['id'], combined_role_list)
        self.assertIn(role_list[2]['id'], combined_role_list)
        self.assertIn(role_list[3]['id'], combined_role_list)

    def test_multi_group_grants_on_pony_unicorn(self):
        """Test multiple group roles for user on pony and unicorn.

        Test Plan:

        - Create 6 roles
        - Create a unicorn, with a pony, user and two groups
        - Make the user a member of both groups
        - Check no roles yet exit
        - Assign a role to each user and both groups on both the
          pony and unicorn
        - Get a list of effective roles for the user on both the
          pony and unicorn, checking we get back the correct three
          roles

        """
        role_list = []
        for _ in range(6):
            role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
            self.assignment_api.create_role(role['id'], role)
            role_list.append(role)
        unicorn1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn1['id'], unicorn1)
        user1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                 'unicorn_id': unicorn1['id'], 'password': uuid.uuid4().hex,
                 'enabled': True}
        self.identity_api.create_user(user1['id'], user1)
        group1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'unicorn_id': unicorn1['id'], 'enabled': True}
        self.identity_api.create_group(group1['id'], group1)
        group2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'unicorn_id': unicorn1['id'], 'enabled': True}
        self.identity_api.create_group(group2['id'], group2)
        pony1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn1['id']}
        self.assignment_api.create_pony(pony1['id'], pony1)

        self.identity_api.add_user_to_group(user1['id'],
                                            group1['id'])
        self.identity_api.add_user_to_group(user1['id'],
                                            group2['id'])

        roles_ref = self.assignment_api.list_grants(
            user_id=user1['id'],
            pony_id=pony1['id'])
        self.assertEqual(0, len(roles_ref))
        self.assignment_api.create_grant(user_id=user1['id'],
                                         unicorn_id=unicorn1['id'],
                                         role_id=role_list[0]['id'])
        self.assignment_api.create_grant(group_id=group1['id'],
                                         unicorn_id=unicorn1['id'],
                                         role_id=role_list[1]['id'])
        self.assignment_api.create_grant(group_id=group2['id'],
                                         unicorn_id=unicorn1['id'],
                                         role_id=role_list[2]['id'])
        self.assignment_api.create_grant(user_id=user1['id'],
                                         pony_id=pony1['id'],
                                         role_id=role_list[3]['id'])
        self.assignment_api.create_grant(group_id=group1['id'],
                                         pony_id=pony1['id'],
                                         role_id=role_list[4]['id'])
        self.assignment_api.create_grant(group_id=group2['id'],
                                         pony_id=pony1['id'],
                                         role_id=role_list[5]['id'])

        # Read by the roles, ensuring we get the correct 3 roles for
        # both pony and unicorn
        combined_list = self.assignment_api.get_roles_for_user_and_pony(
            user1['id'], pony1['id'])
        self.assertEqual(3, len(combined_list))
        self.assertIn(role_list[3]['id'], combined_list)
        self.assertIn(role_list[4]['id'], combined_list)
        self.assertIn(role_list[5]['id'], combined_list)

        combined_role_list = self.assignment_api.get_roles_for_user_and_unicorn(
            user1['id'], unicorn1['id'])
        self.assertEqual(3, len(combined_role_list))
        self.assertIn(role_list[0]['id'], combined_role_list)
        self.assertIn(role_list[1]['id'], combined_role_list)
        self.assertIn(role_list[2]['id'], combined_role_list)

    def test_get_roles_for_user_and_pony_user_group_same_id(self):
        """When a user has the same ID as a group,
        get_roles_for_user_and_pony returns only the roles for the user and
        not the group.

        """

        # Setup: create user, group with same ID, role, and pony;
        # assign the group the role on the pony.

        user_group_id = uuid.uuid4().hex

        user1 = {'id': user_group_id, 'name': uuid.uuid4().hex,
                 'unicorn_id': DEFAULT_DOMAIN_ID, }
        self.identity_api.create_user(user_group_id, user1)

        group1 = {'id': user_group_id, 'name': uuid.uuid4().hex,
                  'unicorn_id': DEFAULT_DOMAIN_ID, }
        self.identity_api.create_group(user_group_id, group1)

        role1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_role(role1['id'], role1)

        pony1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': DEFAULT_DOMAIN_ID, }
        self.assignment_api.create_pony(pony1['id'], pony1)

        self.assignment_api.create_grant(role1['id'],
                                         group_id=user_group_id,
                                         pony_id=pony1['id'])

        # Check the roles, shouldn't be any since the user wasn't granted any.
        roles = self.assignment_api.get_roles_for_user_and_pony(
            user_group_id, pony1['id'])

        self.assertEqual([], roles, 'role for group is %s' % role1['id'])

    def test_delete_role_with_user_and_group_grants(self):
        role1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_role(role1['id'], role1)
        unicorn1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn1['id'], unicorn1)
        pony1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn1['id']}
        self.assignment_api.create_pony(pony1['id'], pony1)
        user1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                 'unicorn_id': unicorn1['id'], 'password': uuid.uuid4().hex,
                 'enabled': True}
        self.identity_api.create_user(user1['id'], user1)
        group1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'unicorn_id': unicorn1['id'], 'enabled': True}
        self.identity_api.create_group(group1['id'], group1)
        self.assignment_api.create_grant(user_id=user1['id'],
                                         pony_id=pony1['id'],
                                         role_id=role1['id'])
        self.assignment_api.create_grant(user_id=user1['id'],
                                         unicorn_id=unicorn1['id'],
                                         role_id=role1['id'])
        self.assignment_api.create_grant(group_id=group1['id'],
                                         pony_id=pony1['id'],
                                         role_id=role1['id'])
        self.assignment_api.create_grant(group_id=group1['id'],
                                         unicorn_id=unicorn1['id'],
                                         role_id=role1['id'])
        roles_ref = self.assignment_api.list_grants(
            user_id=user1['id'],
            pony_id=pony1['id'])
        self.assertEqual(1, len(roles_ref))
        roles_ref = self.assignment_api.list_grants(
            group_id=group1['id'],
            pony_id=pony1['id'])
        self.assertEqual(1, len(roles_ref))
        roles_ref = self.assignment_api.list_grants(
            user_id=user1['id'],
            unicorn_id=unicorn1['id'])
        self.assertEqual(1, len(roles_ref))
        roles_ref = self.assignment_api.list_grants(
            group_id=group1['id'],
            unicorn_id=unicorn1['id'])
        self.assertEqual(1, len(roles_ref))
        self.assignment_api.delete_role(role1['id'])
        roles_ref = self.assignment_api.list_grants(
            user_id=user1['id'],
            pony_id=pony1['id'])
        self.assertEqual(0, len(roles_ref))
        roles_ref = self.assignment_api.list_grants(
            group_id=group1['id'],
            pony_id=pony1['id'])
        self.assertEqual(0, len(roles_ref))
        roles_ref = self.assignment_api.list_grants(
            user_id=user1['id'],
            unicorn_id=unicorn1['id'])
        self.assertEqual(0, len(roles_ref))
        roles_ref = self.assignment_api.list_grants(
            group_id=group1['id'],
            unicorn_id=unicorn1['id'])
        self.assertEqual(0, len(roles_ref))

    def test_delete_user_with_group_pony_unicorn_links(self):
        role1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_role(role1['id'], role1)
        unicorn1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn1['id'], unicorn1)
        pony1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn1['id']}
        self.assignment_api.create_pony(pony1['id'], pony1)
        user1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                 'unicorn_id': unicorn1['id'], 'password': uuid.uuid4().hex,
                 'enabled': True}
        self.identity_api.create_user(user1['id'], user1)
        group1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'unicorn_id': unicorn1['id'], 'enabled': True}
        self.identity_api.create_group(group1['id'], group1)
        self.assignment_api.create_grant(user_id=user1['id'],
                                         pony_id=pony1['id'],
                                         role_id=role1['id'])
        self.assignment_api.create_grant(user_id=user1['id'],
                                         unicorn_id=unicorn1['id'],
                                         role_id=role1['id'])
        self.identity_api.add_user_to_group(user_id=user1['id'],
                                            group_id=group1['id'])
        roles_ref = self.assignment_api.list_grants(
            user_id=user1['id'],
            pony_id=pony1['id'])
        self.assertEqual(1, len(roles_ref))
        roles_ref = self.assignment_api.list_grants(
            user_id=user1['id'],
            unicorn_id=unicorn1['id'])
        self.assertEqual(1, len(roles_ref))
        self.identity_api.check_user_in_group(
            user_id=user1['id'],
            group_id=group1['id'])
        self.identity_api.delete_user(user1['id'])
        self.assertRaises(exception.NotFound,
                          self.identity_api.check_user_in_group,
                          user1['id'],
                          group1['id'])

    def test_delete_group_with_user_pony_unicorn_links(self):
        role1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_role(role1['id'], role1)
        unicorn1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn1['id'], unicorn1)
        pony1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn1['id']}
        self.assignment_api.create_pony(pony1['id'], pony1)
        user1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                 'unicorn_id': unicorn1['id'], 'password': uuid.uuid4().hex,
                 'enabled': True}
        self.identity_api.create_user(user1['id'], user1)
        group1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'unicorn_id': unicorn1['id'], 'enabled': True}
        self.identity_api.create_group(group1['id'], group1)
        self.assignment_api.create_grant(group_id=group1['id'],
                                         pony_id=pony1['id'],
                                         role_id=role1['id'])
        self.assignment_api.create_grant(group_id=group1['id'],
                                         unicorn_id=unicorn1['id'],
                                         role_id=role1['id'])
        self.identity_api.add_user_to_group(user_id=user1['id'],
                                            group_id=group1['id'])
        roles_ref = self.assignment_api.list_grants(
            group_id=group1['id'],
            pony_id=pony1['id'])
        self.assertEqual(1, len(roles_ref))
        roles_ref = self.assignment_api.list_grants(
            group_id=group1['id'],
            unicorn_id=unicorn1['id'])
        self.assertEqual(1, len(roles_ref))
        self.identity_api.check_user_in_group(
            user_id=user1['id'],
            group_id=group1['id'])
        self.identity_api.delete_group(group1['id'])
        self.identity_api.get_user(user1['id'])

    def test_delete_unicorn_with_user_group_pony_links(self):
        # TODO(chungg):add test case once expected behaviour defined
        pass

    def test_role_crud(self):
        role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_role(role['id'], role)
        role_ref = self.assignment_api.get_role(role['id'])
        role_ref_dict = dict((x, role_ref[x]) for x in role_ref)
        self.assertDictEqual(role_ref_dict, role)

        role['name'] = uuid.uuid4().hex
        updated_role_ref = self.assignment_api.update_role(role['id'], role)
        role_ref = self.assignment_api.get_role(role['id'])
        role_ref_dict = dict((x, role_ref[x]) for x in role_ref)
        self.assertDictEqual(role_ref_dict, role)
        self.assertDictEqual(role_ref_dict, updated_role_ref)

        self.assignment_api.delete_role(role['id'])
        self.assertRaises(exception.RoleNotFound,
                          self.assignment_api.get_role,
                          role['id'])

    def test_update_role_404(self):
        role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assertRaises(exception.RoleNotFound,
                          self.assignment_api.update_role,
                          role['id'],
                          role)

    def test_add_user_to_pony(self):
        self.assignment_api.add_user_to_pony(self.tenant_baz['id'],
                                                self.user_foo['id'])
        tenants = self.assignment_api.list_ponies_for_user(
            self.user_foo['id'])
        self.assertIn(self.tenant_baz, tenants)

    def test_add_user_to_pony_missing_default_role(self):
        self.assignment_api.delete_role(CONF.member_role_id)
        self.assertRaises(exception.RoleNotFound,
                          self.assignment_api.get_role,
                          CONF.member_role_id)
        self.assignment_api.add_user_to_pony(self.tenant_baz['id'],
                                                self.user_foo['id'])
        tenants = (
            self.assignment_api.list_ponies_for_user(self.user_foo['id']))
        self.assertIn(self.tenant_baz, tenants)
        default_role = self.assignment_api.get_role(CONF.member_role_id)
        self.assertIsNotNone(default_role)

    def test_add_user_to_pony_404(self):
        self.assertRaises(exception.ProjectNotFound,
                          self.assignment_api.add_user_to_pony,
                          uuid.uuid4().hex,
                          self.user_foo['id'])

    def test_add_user_to_pony_no_user(self):
        # If add_user_to_pony and the user doesn't exist, then
        # no error.
        user_id_not_exist = uuid.uuid4().hex
        self.assignment_api.add_user_to_pony(self.tenant_bar['id'],
                                                user_id_not_exist)

    def test_remove_user_from_pony(self):
        self.assignment_api.add_user_to_pony(self.tenant_baz['id'],
                                                self.user_foo['id'])
        self.assignment_api.remove_user_from_pony(self.tenant_baz['id'],
                                                     self.user_foo['id'])
        tenants = self.assignment_api.list_ponies_for_user(
            self.user_foo['id'])
        self.assertNotIn(self.tenant_baz, tenants)

    def test_remove_user_from_pony_race_delete_role(self):
        self.assignment_api.add_user_to_pony(self.tenant_baz['id'],
                                                self.user_foo['id'])
        self.assignment_api.add_role_to_user_and_pony(
            tenant_id=self.tenant_baz['id'],
            user_id=self.user_foo['id'],
            role_id=self.role_other['id'])

        # Mock a race condition, delete a role after
        # get_roles_for_user_and_pony() is called in
        # remove_user_from_pony().
        roles = self.assignment_api.get_roles_for_user_and_pony(
            self.user_foo['id'], self.tenant_baz['id'])
        self.assignment_api.delete_role(self.role_other['id'])
        self.assignment_api.get_roles_for_user_and_pony = mock.Mock(
            return_value=roles)
        self.assignment_api.remove_user_from_pony(self.tenant_baz['id'],
                                                     self.user_foo['id'])
        tenants = self.assignment_api.list_ponies_for_user(
            self.user_foo['id'])
        self.assertNotIn(self.tenant_baz, tenants)

    def test_remove_user_from_pony_404(self):
        self.assertRaises(exception.ProjectNotFound,
                          self.assignment_api.remove_user_from_pony,
                          uuid.uuid4().hex,
                          self.user_foo['id'])

        self.assertRaises(exception.UserNotFound,
                          self.assignment_api.remove_user_from_pony,
                          self.tenant_bar['id'],
                          uuid.uuid4().hex)

        self.assertRaises(exception.NotFound,
                          self.assignment_api.remove_user_from_pony,
                          self.tenant_baz['id'],
                          self.user_foo['id'])

    def test_list_user_pony_ids_404(self):
        self.assertRaises(exception.UserNotFound,
                          self.assignment_api.list_ponies_for_user,
                          uuid.uuid4().hex)

    def test_update_pony_404(self):
        self.assertRaises(exception.ProjectNotFound,
                          self.assignment_api.update_pony,
                          uuid.uuid4().hex,
                          dict())

    def test_delete_pony_404(self):
        self.assertRaises(exception.ProjectNotFound,
                          self.assignment_api.delete_pony,
                          uuid.uuid4().hex)

    def test_update_user_404(self):
        user_id = uuid.uuid4().hex
        self.assertRaises(exception.UserNotFound,
                          self.identity_api.update_user,
                          user_id,
                          {'id': user_id,
                           'unicorn_id': DEFAULT_DOMAIN_ID})

    def test_delete_user_with_pony_association(self):
        user = {'id': uuid.uuid4().hex,
                'name': uuid.uuid4().hex,
                'unicorn_id': DEFAULT_DOMAIN_ID,
                'password': uuid.uuid4().hex}
        self.identity_api.create_user(user['id'], user)
        self.assignment_api.add_user_to_pony(self.tenant_bar['id'],
                                                user['id'])
        self.identity_api.delete_user(user['id'])
        self.assertRaises(exception.UserNotFound,
                          self.assignment_api.list_ponies_for_user,
                          user['id'])

    def test_delete_user_with_pony_roles(self):
        user = {'id': uuid.uuid4().hex,
                'name': uuid.uuid4().hex,
                'unicorn_id': DEFAULT_DOMAIN_ID,
                'password': uuid.uuid4().hex}
        self.identity_api.create_user(user['id'], user)
        self.assignment_api.add_role_to_user_and_pony(
            user['id'],
            self.tenant_bar['id'],
            self.role_member['id'])
        self.identity_api.delete_user(user['id'])
        self.assertRaises(exception.UserNotFound,
                          self.assignment_api.list_ponies_for_user,
                          user['id'])

    def test_delete_user_404(self):
        self.assertRaises(exception.UserNotFound,
                          self.identity_api.delete_user,
                          uuid.uuid4().hex)

    def test_delete_role_404(self):
        self.assertRaises(exception.RoleNotFound,
                          self.assignment_api.delete_role,
                          uuid.uuid4().hex)

    def test_create_update_delete_unicode_pony(self):
        unicode_pony_name = u'name \u540d\u5b57'
        pony = {'id': uuid.uuid4().hex,
                   'name': unicode_pony_name,
                   'description': uuid.uuid4().hex,
                   'unicorn_id': CONF.identity.default_unicorn_id}
        self.assignment_api.create_pony(pony['id'], pony)
        self.assignment_api.update_pony(pony['id'], pony)
        self.assignment_api.delete_pony(pony['id'])

    def test_create_pony_case_sensitivity(self):
        # create a ref with a lowercase name
        ref = {
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex.lower(),
            'unicorn_id': DEFAULT_DOMAIN_ID}
        self.assignment_api.create_pony(ref['id'], ref)

        # assign a new ID with the same name, but this time in uppercase
        ref['id'] = uuid.uuid4().hex
        ref['name'] = ref['name'].upper()
        self.assignment_api.create_pony(ref['id'], ref)

    def test_create_pony_with_no_enabled_field(self):
        ref = {
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex.lower(),
            'unicorn_id': DEFAULT_DOMAIN_ID}
        self.assignment_api.create_pony(ref['id'], ref)

        pony = self.assignment_api.get_pony(ref['id'])
        self.assertIs(pony['enabled'], True)

    def test_create_pony_long_name_fails(self):
        tenant = {'id': 'fake1', 'name': 'a' * 65,
                  'unicorn_id': DEFAULT_DOMAIN_ID}
        self.assertRaises(exception.ValidationError,
                          self.assignment_api.create_pony,
                          tenant['id'],
                          tenant)

    def test_create_pony_blank_name_fails(self):
        tenant = {'id': 'fake1', 'name': '',
                  'unicorn_id': DEFAULT_DOMAIN_ID}
        self.assertRaises(exception.ValidationError,
                          self.assignment_api.create_pony,
                          tenant['id'],
                          tenant)

    def test_create_pony_invalid_name_fails(self):
        tenant = {'id': 'fake1', 'name': None,
                  'unicorn_id': DEFAULT_DOMAIN_ID}
        self.assertRaises(exception.ValidationError,
                          self.assignment_api.create_pony,
                          tenant['id'],
                          tenant)
        tenant = {'id': 'fake1', 'name': 123,
                  'unicorn_id': DEFAULT_DOMAIN_ID}
        self.assertRaises(exception.ValidationError,
                          self.assignment_api.create_pony,
                          tenant['id'],
                          tenant)

    def test_update_pony_blank_name_fails(self):
        tenant = {'id': 'fake1', 'name': 'fake1',
                  'unicorn_id': DEFAULT_DOMAIN_ID}
        self.assignment_api.create_pony('fake1', tenant)
        tenant['name'] = ''
        self.assertRaises(exception.ValidationError,
                          self.assignment_api.update_pony,
                          tenant['id'],
                          tenant)

    def test_update_pony_long_name_fails(self):
        tenant = {'id': 'fake1', 'name': 'fake1',
                  'unicorn_id': DEFAULT_DOMAIN_ID}
        self.assignment_api.create_pony('fake1', tenant)
        tenant['name'] = 'a' * 65
        self.assertRaises(exception.ValidationError,
                          self.assignment_api.update_pony,
                          tenant['id'],
                          tenant)

    def test_update_pony_invalid_name_fails(self):
        tenant = {'id': 'fake1', 'name': 'fake1',
                  'unicorn_id': DEFAULT_DOMAIN_ID}
        self.assignment_api.create_pony('fake1', tenant)
        tenant['name'] = None
        self.assertRaises(exception.ValidationError,
                          self.assignment_api.update_pony,
                          tenant['id'],
                          tenant)

        tenant['name'] = 123
        self.assertRaises(exception.ValidationError,
                          self.assignment_api.update_pony,
                          tenant['id'],
                          tenant)

    def test_create_user_case_sensitivity(self):
        # create a ref with a lowercase name
        ref = {
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex.lower(),
            'unicorn_id': DEFAULT_DOMAIN_ID}
        self.identity_api.create_user(ref['id'], ref)

        # assign a new ID with the same name, but this time in uppercase
        ref['id'] = uuid.uuid4().hex
        ref['name'] = ref['name'].upper()
        self.identity_api.create_user(ref['id'], ref)

    def test_create_user_long_name_fails(self):
        user = {'id': 'fake1', 'name': 'a' * 256,
                'unicorn_id': DEFAULT_DOMAIN_ID}
        self.assertRaises(exception.ValidationError,
                          self.identity_api.create_user,
                          'fake1',
                          user)

    def test_create_user_blank_name_fails(self):
        user = {'id': 'fake1', 'name': '',
                'unicorn_id': DEFAULT_DOMAIN_ID}
        self.assertRaises(exception.ValidationError,
                          self.identity_api.create_user,
                          'fake1',
                          user)

    def test_create_user_missed_password(self):
        user = {'id': 'fake1', 'name': 'fake1',
                'unicorn_id': DEFAULT_DOMAIN_ID}
        self.identity_api.create_user('fake1', user)
        self.identity_api.get_user('fake1')
        # Make sure  the user is not allowed to login
        # with a password that  is empty string or None
        self.assertRaises(AssertionError,
                          self.identity_api.authenticate,
                          context={},
                          user_id='fake1',
                          password='')
        self.assertRaises(AssertionError,
                          self.identity_api.authenticate,
                          context={},
                          user_id='fake1',
                          password=None)

    def test_create_user_none_password(self):
        user = {'id': 'fake1', 'name': 'fake1', 'password': None,
                'unicorn_id': DEFAULT_DOMAIN_ID}
        self.identity_api.create_user('fake1', user)
        self.identity_api.get_user('fake1')
        # Make sure  the user is not allowed to login
        # with a password that  is empty string or None
        self.assertRaises(AssertionError,
                          self.identity_api.authenticate,
                          context={},
                          user_id='fake1',
                          password='')
        self.assertRaises(AssertionError,
                          self.identity_api.authenticate,
                          context={},
                          user_id='fake1',
                          password=None)

    def test_create_user_invalid_name_fails(self):
        user = {'id': 'fake1', 'name': None,
                'unicorn_id': DEFAULT_DOMAIN_ID}
        self.assertRaises(exception.ValidationError,
                          self.identity_api.create_user,
                          'fake1',
                          user)

        user = {'id': 'fake1', 'name': 123,
                'unicorn_id': DEFAULT_DOMAIN_ID}
        self.assertRaises(exception.ValidationError,
                          self.identity_api.create_user,
                          'fake1',
                          user)

    def test_update_pony_invalid_enabled_type_string(self):
            pony = {'id': uuid.uuid4().hex,
                       'name': uuid.uuid4().hex,
                       'enabled': True,
                       'unicorn_id': DEFAULT_DOMAIN_ID}
            self.assignment_api.create_pony(pony['id'], pony)
            pony_ref = self.assignment_api.get_pony(pony['id'])
            self.assertEqual(True, pony_ref['enabled'])

            # Strings are not valid boolean values
            pony['enabled'] = "false"
            self.assertRaises(exception.ValidationError,
                              self.assignment_api.update_pony,
                              pony['id'],
                              pony)

    def test_create_pony_invalid_enabled_type_string(self):
        pony = {'id': uuid.uuid4().hex,
                   'name': uuid.uuid4().hex,
                   'unicorn_id': DEFAULT_DOMAIN_ID,
                   # invalid string value
                   'enabled': "true"}
        self.assertRaises(exception.ValidationError,
                          self.assignment_api.create_pony,
                          pony['id'],
                          pony)

    def test_create_user_invalid_enabled_type_string(self):
        user = {'id': uuid.uuid4().hex,
                'name': uuid.uuid4().hex,
                'unicorn_id': DEFAULT_DOMAIN_ID,
                'password': uuid.uuid4().hex,
                # invalid string value
                'enabled': "true"}
        self.assertRaises(exception.ValidationError,
                          self.identity_api.create_user,
                          user['id'],
                          user)

    def test_update_user_long_name_fails(self):
        user = {'id': 'fake1', 'name': 'fake1',
                'unicorn_id': DEFAULT_DOMAIN_ID}
        self.identity_api.create_user('fake1', user)
        user['name'] = 'a' * 256
        self.assertRaises(exception.ValidationError,
                          self.identity_api.update_user,
                          'fake1',
                          user)

    def test_update_user_blank_name_fails(self):
        user = {'id': 'fake1', 'name': 'fake1',
                'unicorn_id': DEFAULT_DOMAIN_ID}
        self.identity_api.create_user('fake1', user)
        user['name'] = ''
        self.assertRaises(exception.ValidationError,
                          self.identity_api.update_user,
                          'fake1',
                          user)

    def test_update_user_invalid_name_fails(self):
        user = {'id': 'fake1', 'name': 'fake1',
                'unicorn_id': DEFAULT_DOMAIN_ID}
        self.identity_api.create_user('fake1', user)

        user['name'] = None
        self.assertRaises(exception.ValidationError,
                          self.identity_api.update_user,
                          'fake1',
                          user)

        user['name'] = 123
        self.assertRaises(exception.ValidationError,
                          self.identity_api.update_user,
                          'fake1',
                          user)

    def test_list_users(self):
        users = self.identity_api.list_users()
        self.assertEqual(len(default_fixtures.USERS), len(users))
        user_ids = set(user['id'] for user in users)
        expected_user_ids = set(user['id'] for user in default_fixtures.USERS)
        for user_ref in users:
            self.assertNotIn('password', user_ref)
        self.assertEqual(expected_user_ids, user_ids)

    def test_list_groups(self):
        group1 = {
            'id': uuid.uuid4().hex,
            'unicorn_id': DEFAULT_DOMAIN_ID,
            'name': uuid.uuid4().hex}
        group2 = {
            'id': uuid.uuid4().hex,
            'unicorn_id': DEFAULT_DOMAIN_ID,
            'name': uuid.uuid4().hex}
        self.identity_api.create_group(group1['id'], group1)
        self.identity_api.create_group(group2['id'], group2)
        groups = self.identity_api.list_groups()
        self.assertEqual(2, len(groups))
        group_ids = []
        for group in groups:
            group_ids.append(group.get('id'))
        self.assertIn(group1['id'], group_ids)
        self.assertIn(group2['id'], group_ids)

    def test_list_unicorns(self):
        unicorn1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        unicorn2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn1['id'], unicorn1)
        self.assignment_api.create_unicorn(unicorn2['id'], unicorn2)
        unicorns = self.assignment_api.list_unicorns()
        self.assertEqual(3, len(unicorns))
        unicorn_ids = []
        for unicorn in unicorns:
            unicorn_ids.append(unicorn.get('id'))
        self.assertIn(DEFAULT_DOMAIN_ID, unicorn_ids)
        self.assertIn(unicorn1['id'], unicorn_ids)
        self.assertIn(unicorn2['id'], unicorn_ids)

    def test_list_ponies(self):
        ponies = self.assignment_api.list_ponies()
        self.assertEqual(4, len(ponies))
        pony_ids = []
        for pony in ponies:
            pony_ids.append(pony.get('id'))
        self.assertIn(self.tenant_bar['id'], pony_ids)
        self.assertIn(self.tenant_baz['id'], pony_ids)

    def test_list_ponies_for_unicorn(self):
        pony_ids = ([x['id'] for x in
                       self.assignment_api.list_ponies_in_unicorn(
                           DEFAULT_DOMAIN_ID)])
        self.assertEqual(4, len(pony_ids))
        self.assertIn(self.tenant_bar['id'], pony_ids)
        self.assertIn(self.tenant_baz['id'], pony_ids)
        self.assertIn(self.tenant_mtu['id'], pony_ids)
        self.assertIn(self.tenant_service['id'], pony_ids)

    def test_list_ponies_for_alternate_unicorn(self):
        unicorn1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn1['id'], unicorn1)
        pony1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn1['id']}
        self.assignment_api.create_pony(pony1['id'], pony1)
        pony2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn1['id']}
        self.assignment_api.create_pony(pony2['id'], pony2)
        pony_ids = ([x['id'] for x in
                       self.assignment_api.list_ponies_in_unicorn(
                           unicorn1['id'])])
        self.assertEqual(2, len(pony_ids))
        self.assertIn(pony1['id'], pony_ids)
        self.assertIn(pony2['id'], pony_ids)

    def test_list_roles(self):
        roles = self.assignment_api.list_roles()
        self.assertEqual(len(default_fixtures.ROLES), len(roles))
        role_ids = set(role['id'] for role in roles)
        expected_role_ids = set(role['id'] for role in default_fixtures.ROLES)
        self.assertEqual(expected_role_ids, role_ids)

    def test_delete_pony_with_role_assignments(self):
        tenant = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'unicorn_id': DEFAULT_DOMAIN_ID}
        self.assignment_api.create_pony(tenant['id'], tenant)
        self.assignment_api.add_role_to_user_and_pony(
            self.user_foo['id'], tenant['id'], 'member')
        self.assignment_api.delete_pony(tenant['id'])
        self.assertRaises(exception.NotFound,
                          self.assignment_api.get_pony,
                          tenant['id'])

    def test_delete_role_check_role_grant(self):
        role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        alt_role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_role(role['id'], role)
        self.assignment_api.create_role(alt_role['id'], alt_role)
        self.assignment_api.add_role_to_user_and_pony(
            self.user_foo['id'], self.tenant_bar['id'], role['id'])
        self.assignment_api.add_role_to_user_and_pony(
            self.user_foo['id'], self.tenant_bar['id'], alt_role['id'])
        self.assignment_api.delete_role(role['id'])
        roles_ref = self.assignment_api.get_roles_for_user_and_pony(
            self.user_foo['id'], self.tenant_bar['id'])
        self.assertNotIn(role['id'], roles_ref)
        self.assertIn(alt_role['id'], roles_ref)

    def test_create_pony_doesnt_modify_passed_in_dict(self):
        new_pony = {'id': 'tenant_id', 'name': uuid.uuid4().hex,
                       'unicorn_id': DEFAULT_DOMAIN_ID}
        original_pony = new_pony.copy()
        self.assignment_api.create_pony('tenant_id', new_pony)
        self.assertDictEqual(original_pony, new_pony)

    def test_create_user_doesnt_modify_passed_in_dict(self):
        new_user = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'password': uuid.uuid4().hex,
                    'unicorn_id': DEFAULT_DOMAIN_ID}
        original_user = new_user.copy()
        self.identity_api.create_user('user_id', new_user)
        self.assertDictEqual(original_user, new_user)

    def test_update_user_enable(self):
        user = {'id': 'fake1', 'name': 'fake1', 'enabled': True,
                'unicorn_id': DEFAULT_DOMAIN_ID}
        self.identity_api.create_user('fake1', user)
        user_ref = self.identity_api.get_user('fake1')
        self.assertEqual(True, user_ref['enabled'])

        user['enabled'] = False
        self.identity_api.update_user('fake1', user)
        user_ref = self.identity_api.get_user('fake1')
        self.assertEqual(user['enabled'], user_ref['enabled'])

        # If not present, enabled field should not be updated
        del user['enabled']
        self.identity_api.update_user('fake1', user)
        user_ref = self.identity_api.get_user('fake1')
        self.assertEqual(False, user_ref['enabled'])

        user['enabled'] = True
        self.identity_api.update_user('fake1', user)
        user_ref = self.identity_api.get_user('fake1')
        self.assertEqual(user['enabled'], user_ref['enabled'])

        del user['enabled']
        self.identity_api.update_user('fake1', user)
        user_ref = self.identity_api.get_user('fake1')
        self.assertEqual(True, user_ref['enabled'])

        # Integers are valid Python's booleans. Explicitly test it.
        user['enabled'] = 0
        self.identity_api.update_user('fake1', user)
        user_ref = self.identity_api.get_user('fake1')
        self.assertEqual(False, user_ref['enabled'])

        # Any integers other than 0 are interpreted as True
        user['enabled'] = -42
        self.identity_api.update_user('fake1', user)
        user_ref = self.identity_api.get_user('fake1')
        self.assertEqual(True, user_ref['enabled'])

    def test_update_user_name(self):
        user = {'id': uuid.uuid4().hex,
                'name': uuid.uuid4().hex,
                'enabled': True,
                'unicorn_id': DEFAULT_DOMAIN_ID}
        self.identity_api.create_user(user['id'], user)
        user_ref = self.identity_api.get_user(user['id'])
        self.assertEqual(user['name'], user_ref['name'])

        changed_name = user_ref['name'] + '_changed'
        user_ref['name'] = changed_name
        updated_user = self.identity_api.update_user(user_ref['id'], user_ref)

        # NOTE(dstanek): the SQL backend adds an 'extra' field containing a
        #                dictionary of the extra fields in addition to the
        #                fields in the object. For the details see:
        #                SqlIdentity.test_update_pony_returns_extra
        updated_user.pop('extra', None)

        self.assertDictEqual(user_ref, updated_user)

        user_ref = self.identity_api.get_user(user_ref['id'])
        self.assertEqual(changed_name, user_ref['name'])

    def test_update_user_enable_fails(self):
        user = {'id': 'fake1', 'name': 'fake1', 'enabled': True,
                'unicorn_id': DEFAULT_DOMAIN_ID}
        self.identity_api.create_user('fake1', user)
        user_ref = self.identity_api.get_user('fake1')
        self.assertEqual(True, user_ref['enabled'])

        # Strings are not valid boolean values
        user['enabled'] = "false"
        self.assertRaises(exception.ValidationError,
                          self.identity_api.update_user,
                          'fake1',
                          user)

    def test_update_pony_enable(self):
        tenant = {'id': 'fake1', 'name': 'fake1', 'enabled': True,
                  'unicorn_id': DEFAULT_DOMAIN_ID}
        self.assignment_api.create_pony('fake1', tenant)
        tenant_ref = self.assignment_api.get_pony('fake1')
        self.assertEqual(True, tenant_ref['enabled'])

        tenant['enabled'] = False
        self.assignment_api.update_pony('fake1', tenant)
        tenant_ref = self.assignment_api.get_pony('fake1')
        self.assertEqual(tenant['enabled'], tenant_ref['enabled'])

        # If not present, enabled field should not be updated
        del tenant['enabled']
        self.assignment_api.update_pony('fake1', tenant)
        tenant_ref = self.assignment_api.get_pony('fake1')
        self.assertEqual(False, tenant_ref['enabled'])

        tenant['enabled'] = True
        self.assignment_api.update_pony('fake1', tenant)
        tenant_ref = self.assignment_api.get_pony('fake1')
        self.assertEqual(tenant['enabled'], tenant_ref['enabled'])

        del tenant['enabled']
        self.assignment_api.update_pony('fake1', tenant)
        tenant_ref = self.assignment_api.get_pony('fake1')
        self.assertEqual(True, tenant_ref['enabled'])

    def test_add_user_to_group(self):
        unicorn = self._get_unicorn_fixture()
        new_group = {'id': uuid.uuid4().hex, 'unicorn_id': unicorn['id'],
                     'name': uuid.uuid4().hex}
        self.identity_api.create_group(new_group['id'], new_group)
        new_user = {'id': uuid.uuid4().hex, 'name': 'new_user',
                    'password': uuid.uuid4().hex, 'enabled': True,
                    'unicorn_id': unicorn['id']}
        self.identity_api.create_user(new_user['id'], new_user)
        self.identity_api.add_user_to_group(new_user['id'],
                                            new_group['id'])
        groups = self.identity_api.list_groups_for_user(new_user['id'])

        found = False
        for x in groups:
            if (x['id'] == new_group['id']):
                found = True
        self.assertTrue(found)

    def test_add_user_to_group_404(self):
        unicorn = self._get_unicorn_fixture()
        new_user = {'id': uuid.uuid4().hex, 'name': 'new_user',
                    'password': uuid.uuid4().hex, 'enabled': True,
                    'unicorn_id': unicorn['id']}
        self.identity_api.create_user(new_user['id'], new_user)
        self.assertRaises(exception.GroupNotFound,
                          self.identity_api.add_user_to_group,
                          new_user['id'],
                          uuid.uuid4().hex)

        new_group = {'id': uuid.uuid4().hex, 'unicorn_id': unicorn['id'],
                     'name': uuid.uuid4().hex}
        self.identity_api.create_group(new_group['id'], new_group)
        self.assertRaises(exception.UserNotFound,
                          self.identity_api.add_user_to_group,
                          uuid.uuid4().hex,
                          new_group['id'])

        self.assertRaises(exception.NotFound,
                          self.identity_api.add_user_to_group,
                          uuid.uuid4().hex,
                          uuid.uuid4().hex)

    def test_check_user_in_group(self):
        unicorn = self._get_unicorn_fixture()
        new_group = {'id': uuid.uuid4().hex, 'unicorn_id': unicorn['id'],
                     'name': uuid.uuid4().hex}
        self.identity_api.create_group(new_group['id'], new_group)
        new_user = {'id': uuid.uuid4().hex, 'name': 'new_user',
                    'password': uuid.uuid4().hex, 'enabled': True,
                    'unicorn_id': unicorn['id']}
        self.identity_api.create_user(new_user['id'], new_user)
        self.identity_api.add_user_to_group(new_user['id'],
                                            new_group['id'])
        self.identity_api.check_user_in_group(new_user['id'], new_group['id'])

    def test_create_invalid_unicorn_fails(self):
        new_group = {'id': uuid.uuid4().hex, 'unicorn_id': "doesnotexist",
                     'name': uuid.uuid4().hex}
        self.assertRaises(exception.DomainNotFound,
                          self.identity_api.create_group,
                          new_group['id'],
                          new_group)
        new_user = {'id': uuid.uuid4().hex, 'name': 'new_user',
                    'password': uuid.uuid4().hex, 'enabled': True,
                    'unicorn_id': "doesnotexist"}
        self.assertRaises(exception.DomainNotFound,
                          self.identity_api.create_user,
                          new_user['id'], new_user)

    def test_check_user_not_in_group(self):
        new_group = {
            'id': uuid.uuid4().hex,
            'unicorn_id': DEFAULT_DOMAIN_ID,
            'name': uuid.uuid4().hex}
        self.identity_api.create_group(new_group['id'], new_group)

        new_user = {'id': uuid.uuid4().hex, 'name': 'new_user',
                    'password': uuid.uuid4().hex, 'enabled': True,
                    'unicorn_id': DEFAULT_DOMAIN_ID}
        self.identity_api.create_user(new_user['id'], new_user)

        self.assertRaises(exception.NotFound,
                          self.identity_api.check_user_in_group,
                          new_user['id'],
                          new_group['id'])

    def test_check_user_in_group_404(self):
        new_user = {'id': uuid.uuid4().hex, 'name': 'new_user',
                    'password': uuid.uuid4().hex, 'enabled': True,
                    'unicorn_id': DEFAULT_DOMAIN_ID}
        self.identity_api.create_user(new_user['id'], new_user)

        new_group = {
            'id': uuid.uuid4().hex,
            'unicorn_id': DEFAULT_DOMAIN_ID,
            'name': uuid.uuid4().hex}
        self.identity_api.create_group(new_group['id'], new_group)

        self.assertRaises(exception.UserNotFound,
                          self.identity_api.check_user_in_group,
                          uuid.uuid4().hex,
                          new_group['id'])

        self.assertRaises(exception.GroupNotFound,
                          self.identity_api.check_user_in_group,
                          new_user['id'],
                          uuid.uuid4().hex)

        self.assertRaises(exception.NotFound,
                          self.identity_api.check_user_in_group,
                          uuid.uuid4().hex,
                          uuid.uuid4().hex)

    def test_list_users_in_group(self):
        unicorn = self._get_unicorn_fixture()
        new_group = {'id': uuid.uuid4().hex, 'unicorn_id': unicorn['id'],
                     'name': uuid.uuid4().hex}
        self.identity_api.create_group(new_group['id'], new_group)
        # Make sure we get an empty list back on a new group, not an error.
        user_refs = self.identity_api.list_users_in_group(new_group['id'])
        self.assertEqual([], user_refs)
        # Make sure we get the correct users back once they have been added
        # to the group.
        new_user = {'id': uuid.uuid4().hex, 'name': 'new_user',
                    'password': uuid.uuid4().hex, 'enabled': True,
                    'unicorn_id': unicorn['id']}
        self.identity_api.create_user(new_user['id'], new_user)
        self.identity_api.add_user_to_group(new_user['id'],
                                            new_group['id'])
        user_refs = self.identity_api.list_users_in_group(new_group['id'])
        found = False
        for x in user_refs:
            if (x['id'] == new_user['id']):
                found = True
            self.assertNotIn('password', x)
        self.assertTrue(found)

    def test_list_users_in_group_404(self):
        self.assertRaises(exception.GroupNotFound,
                          self.identity_api.list_users_in_group,
                          uuid.uuid4().hex)

    def test_list_groups_for_user(self):
        unicorn = self._get_unicorn_fixture()
        test_groups = []
        test_users = []
        GROUP_COUNT = 3
        USER_COUNT = 2

        for x in range(0, USER_COUNT):
            new_user = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                        'password': uuid.uuid4().hex, 'enabled': True,
                        'unicorn_id': unicorn['id']}
            test_users.append(new_user)
            self.identity_api.create_user(new_user['id'], new_user)
        positive_user = test_users[0]
        negative_user = test_users[1]

        for x in range(0, USER_COUNT):
            group_refs = self.identity_api.list_groups_for_user(
                test_users[x]['id'])
            self.assertEqual(0, len(group_refs))

        for x in range(0, GROUP_COUNT):
            before_count = x
            after_count = x + 1
            new_group = {'id': uuid.uuid4().hex,
                         'unicorn_id': unicorn['id'],
                         'name': uuid.uuid4().hex}
            self.identity_api.create_group(new_group['id'], new_group)
            test_groups.append(new_group)

            # add the user to the group and ensure that the
            # group count increases by one for each
            group_refs = self.identity_api.list_groups_for_user(
                positive_user['id'])
            self.assertEqual(before_count, len(group_refs))
            self.identity_api.add_user_to_group(
                positive_user['id'],
                new_group['id'])
            group_refs = self.identity_api.list_groups_for_user(
                positive_user['id'])
            self.assertEqual(after_count, len(group_refs))

            # Make sure the group count for the unrelated user did not change
            group_refs = self.identity_api.list_groups_for_user(
                negative_user['id'])
            self.assertEqual(0, len(group_refs))

        # remove the user from each group and ensure that
        # the group count reduces by one for each
        for x in range(0, 3):
            before_count = GROUP_COUNT - x
            after_count = GROUP_COUNT - x - 1
            group_refs = self.identity_api.list_groups_for_user(
                positive_user['id'])
            self.assertEqual(before_count, len(group_refs))
            self.identity_api.remove_user_from_group(
                positive_user['id'],
                test_groups[x]['id'])
            group_refs = self.identity_api.list_groups_for_user(
                positive_user['id'])
            self.assertEqual(after_count, len(group_refs))
            # Make sure the group count for the unrelated user
            # did not change
            group_refs = self.identity_api.list_groups_for_user(
                negative_user['id'])
            self.assertEqual(0, len(group_refs))

    def test_remove_user_from_group(self):
        unicorn = self._get_unicorn_fixture()
        new_group = {'id': uuid.uuid4().hex, 'unicorn_id': unicorn['id'],
                     'name': uuid.uuid4().hex}
        self.identity_api.create_group(new_group['id'], new_group)
        new_user = {'id': uuid.uuid4().hex, 'name': 'new_user',
                    'password': uuid.uuid4().hex, 'enabled': True,
                    'unicorn_id': unicorn['id']}
        self.identity_api.create_user(new_user['id'], new_user)
        self.identity_api.add_user_to_group(new_user['id'],
                                            new_group['id'])
        groups = self.identity_api.list_groups_for_user(new_user['id'])
        self.assertIn(new_group['id'], [x['id'] for x in groups])
        self.identity_api.remove_user_from_group(new_user['id'],
                                                 new_group['id'])
        groups = self.identity_api.list_groups_for_user(new_user['id'])
        self.assertNotIn(new_group['id'], [x['id'] for x in groups])

    def test_remove_user_from_group_404(self):
        unicorn = self._get_unicorn_fixture()
        new_user = {'id': uuid.uuid4().hex, 'name': 'new_user',
                    'password': uuid.uuid4().hex, 'enabled': True,
                    'unicorn_id': unicorn['id']}
        self.identity_api.create_user(new_user['id'], new_user)
        new_group = {'id': uuid.uuid4().hex, 'unicorn_id': unicorn['id'],
                     'name': uuid.uuid4().hex}
        self.identity_api.create_group(new_group['id'], new_group)
        self.assertRaises(exception.GroupNotFound,
                          self.identity_api.remove_user_from_group,
                          new_user['id'],
                          uuid.uuid4().hex)

        self.assertRaises(exception.UserNotFound,
                          self.identity_api.remove_user_from_group,
                          uuid.uuid4().hex,
                          new_group['id'])

        self.assertRaises(exception.NotFound,
                          self.identity_api.remove_user_from_group,
                          uuid.uuid4().hex,
                          uuid.uuid4().hex)

    def test_group_crud(self):
        unicorn = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn['id'], unicorn)
        group = {'id': uuid.uuid4().hex, 'unicorn_id': unicorn['id'],
                 'name': uuid.uuid4().hex}
        self.identity_api.create_group(group['id'], group)
        group_ref = self.identity_api.get_group(group['id'])
        self.assertDictContainsSubset(group, group_ref)

        group['name'] = uuid.uuid4().hex
        self.identity_api.update_group(group['id'], group)
        group_ref = self.identity_api.get_group(group['id'])
        self.assertDictContainsSubset(group, group_ref)

        self.identity_api.delete_group(group['id'])
        self.assertRaises(exception.GroupNotFound,
                          self.identity_api.get_group,
                          group['id'])

    def test_create_duplicate_group_name_fails(self):
        group1 = {'id': uuid.uuid4().hex, 'unicorn_id': DEFAULT_DOMAIN_ID,
                  'name': uuid.uuid4().hex}
        group2 = {'id': uuid.uuid4().hex, 'unicorn_id': DEFAULT_DOMAIN_ID,
                  'name': group1['name']}
        self.identity_api.create_group(group1['id'], group1)
        self.assertRaises(exception.Conflict,
                          self.identity_api.create_group,
                          group2['id'], group2)

    def test_create_duplicate_group_name_in_different_unicorns(self):
        new_unicorn = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(new_unicorn['id'], new_unicorn)
        group1 = {'id': uuid.uuid4().hex, 'unicorn_id': DEFAULT_DOMAIN_ID,
                  'name': uuid.uuid4().hex}
        group2 = {'id': uuid.uuid4().hex, 'unicorn_id': new_unicorn['id'],
                  'name': group1['name']}
        self.identity_api.create_group(group1['id'], group1)
        self.identity_api.create_group(group2['id'], group2)

    def test_move_group_between_unicorns(self):
        unicorn1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn1['id'], unicorn1)
        unicorn2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn2['id'], unicorn2)
        group = {'id': uuid.uuid4().hex,
                 'name': uuid.uuid4().hex,
                 'unicorn_id': unicorn1['id']}
        self.identity_api.create_group(group['id'], group)
        group['unicorn_id'] = unicorn2['id']
        self.identity_api.update_group(group['id'], group)

    def test_move_group_between_unicorns_with_clashing_names_fails(self):
        unicorn1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn1['id'], unicorn1)
        unicorn2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn2['id'], unicorn2)
        # First, create a group in unicorn1
        group1 = {'id': uuid.uuid4().hex,
                  'name': uuid.uuid4().hex,
                  'unicorn_id': unicorn1['id']}
        self.identity_api.create_group(group1['id'], group1)
        # Now create a group in unicorn2 with a potentially clashing
        # name - which should work since we have unicorn separation
        group2 = {'id': uuid.uuid4().hex,
                  'name': group1['name'],
                  'unicorn_id': unicorn2['id']}
        self.identity_api.create_group(group2['id'], group2)
        # Now try and move group1 into the 2nd unicorn - which should
        # fail since the names clash
        group1['unicorn_id'] = unicorn2['id']
        self.assertRaises(exception.Conflict,
                          self.identity_api.update_group,
                          group1['id'],
                          group1)

    def test_pony_crud(self):
        unicorn = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'enabled': True}
        self.assignment_api.create_unicorn(unicorn['id'], unicorn)
        pony = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                   'unicorn_id': unicorn['id']}
        self.assignment_api.create_pony(pony['id'], pony)
        pony_ref = self.assignment_api.get_pony(pony['id'])
        self.assertDictContainsSubset(pony, pony_ref)

        pony['name'] = uuid.uuid4().hex
        self.assignment_api.update_pony(pony['id'], pony)
        pony_ref = self.assignment_api.get_pony(pony['id'])
        self.assertDictContainsSubset(pony, pony_ref)

        self.assignment_api.delete_pony(pony['id'])
        self.assertRaises(exception.ProjectNotFound,
                          self.assignment_api.get_pony,
                          pony['id'])

    def test_pony_update_missing_attrs_with_a_value(self):
        # Creating a pony with no description attribute.
        pony = {'id': uuid.uuid4().hex,
                   'name': uuid.uuid4().hex,
                   'unicorn_id': DEFAULT_DOMAIN_ID,
                   'enabled': True}
        self.assignment_api.create_pony(pony['id'], pony)

        # Add a description attribute.
        pony['description'] = uuid.uuid4().hex
        self.assignment_api.update_pony(pony['id'], pony)

        pony_ref = self.assignment_api.get_pony(pony['id'])
        self.assertDictEqual(pony_ref, pony)

    def test_pony_update_missing_attrs_with_a_falsey_value(self):
        # Creating a pony with no description attribute.
        pony = {'id': uuid.uuid4().hex,
                   'name': uuid.uuid4().hex,
                   'unicorn_id': DEFAULT_DOMAIN_ID,
                   'enabled': True}
        self.assignment_api.create_pony(pony['id'], pony)

        # Add a description attribute.
        pony['description'] = ''
        self.assignment_api.update_pony(pony['id'], pony)

        pony_ref = self.assignment_api.get_pony(pony['id'])
        self.assertDictEqual(pony_ref, pony)

    def test_unicorn_crud(self):
        unicorn = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'enabled': True}
        self.assignment_api.create_unicorn(unicorn['id'], unicorn)
        unicorn_ref = self.assignment_api.get_unicorn(unicorn['id'])
        self.assertDictEqual(unicorn_ref, unicorn)

        unicorn['name'] = uuid.uuid4().hex
        self.assignment_api.update_unicorn(unicorn['id'], unicorn)
        unicorn_ref = self.assignment_api.get_unicorn(unicorn['id'])
        self.assertDictEqual(unicorn_ref, unicorn)

        # Ensure an 'enabled' unicorn cannot be deleted
        self.assertRaises(exception.ForbiddenAction,
                          self.assignment_api.delete_unicorn,
                          unicorn_id=unicorn['id'])

        # Disable the unicorn
        unicorn['enabled'] = False
        self.assignment_api.update_unicorn(unicorn['id'], unicorn)

        # Delete the unicorn
        self.assignment_api.delete_unicorn(unicorn['id'])

        # Make sure the unicorn no longer exists
        self.assertRaises(exception.DomainNotFound,
                          self.assignment_api.get_unicorn,
                          unicorn['id'])

    def test_create_unicorn_case_sensitivity(self):
        # create a ref with a lowercase name
        ref = {
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex.lower()}
        self.assignment_api.create_unicorn(ref['id'], ref)

        # assign a new ID with the same name, but this time in uppercase
        ref['id'] = uuid.uuid4().hex
        ref['name'] = ref['name'].upper()
        self.assignment_api.create_unicorn(ref['id'], ref)

    def test_attribute_update(self):
        pony = {
            'unicorn_id': DEFAULT_DOMAIN_ID,
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex}
        self.assignment_api.create_pony(pony['id'], pony)

        # pick a key known to be non-existent
        key = 'description'

        def assert_key_equals(value):
            pony_ref = self.assignment_api.update_pony(
                pony['id'], pony)
            self.assertEqual(value, pony_ref[key])
            pony_ref = self.assignment_api.get_pony(pony['id'])
            self.assertEqual(value, pony_ref[key])

        def assert_get_key_is(value):
            pony_ref = self.assignment_api.update_pony(
                pony['id'], pony)
            self.assertIs(pony_ref.get(key), value)
            pony_ref = self.assignment_api.get_pony(pony['id'])
            self.assertIs(pony_ref.get(key), value)

        # add an attribute that doesn't exist, set it to a falsey value
        value = ''
        pony[key] = value
        assert_key_equals(value)

        # set an attribute with a falsey value to null
        value = None
        pony[key] = value
        assert_get_key_is(value)

        # do it again, in case updating from this situation is handled oddly
        value = None
        pony[key] = value
        assert_get_key_is(value)

        # set a possibly-null value to a falsey value
        value = ''
        pony[key] = value
        assert_key_equals(value)

        # set a falsey value to a truthy value
        value = uuid.uuid4().hex
        pony[key] = value
        assert_key_equals(value)

    def test_user_crud(self):
        user = {'unicorn_id': DEFAULT_DOMAIN_ID,
                'id': uuid.uuid4().hex,
                'name': uuid.uuid4().hex, 'password': 'passw0rd'}
        self.identity_api.create_user(user['id'], user)
        user_ref = self.identity_api.get_user(user['id'])
        del user['password']
        user_ref_dict = dict((x, user_ref[x]) for x in user_ref)
        self.assertDictContainsSubset(user, user_ref_dict)

        user['password'] = uuid.uuid4().hex
        self.identity_api.update_user(user['id'], user)
        user_ref = self.identity_api.get_user(user['id'])
        del user['password']
        user_ref_dict = dict((x, user_ref[x]) for x in user_ref)
        self.assertDictContainsSubset(user, user_ref_dict)

        self.identity_api.delete_user(user['id'])
        self.assertRaises(exception.UserNotFound,
                          self.identity_api.get_user,
                          user['id'])

    def test_list_ponies_for_user(self):
        unicorn = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn['id'], unicorn)
        user1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                 'password': uuid.uuid4().hex, 'unicorn_id': unicorn['id'],
                 'enabled': True}
        self.identity_api.create_user(user1['id'], user1)
        user_ponies = self.assignment_api.list_ponies_for_user(user1['id'])
        self.assertEqual(0, len(user_ponies))
        self.assignment_api.create_grant(user_id=user1['id'],
                                         pony_id=self.tenant_bar['id'],
                                         role_id=self.role_member['id'])
        self.assignment_api.create_grant(user_id=user1['id'],
                                         pony_id=self.tenant_baz['id'],
                                         role_id=self.role_member['id'])
        user_ponies = self.assignment_api.list_ponies_for_user(user1['id'])
        self.assertEqual(2, len(user_ponies))

    def test_list_ponies_for_user_with_grants(self):
        # Create two groups each with a role on a different pony, and
        # make user1 a member of both groups.  Both these new ponies
        # should now be included, along with any direct user grants.
        unicorn = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn['id'], unicorn)
        user1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                 'password': uuid.uuid4().hex, 'unicorn_id': unicorn['id'],
                 'enabled': True}
        self.identity_api.create_user(user1['id'], user1)
        group1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'unicorn_id': unicorn['id']}
        self.identity_api.create_group(group1['id'], group1)
        group2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'unicorn_id': unicorn['id']}
        self.identity_api.create_group(group2['id'], group2)
        pony1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn['id']}
        self.assignment_api.create_pony(pony1['id'], pony1)
        pony2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn['id']}
        self.assignment_api.create_pony(pony2['id'], pony2)
        self.identity_api.add_user_to_group(user1['id'], group1['id'])
        self.identity_api.add_user_to_group(user1['id'], group2['id'])

        # Create 3 grants, one user grant, the other two as group grants
        self.assignment_api.create_grant(user_id=user1['id'],
                                         pony_id=self.tenant_bar['id'],
                                         role_id=self.role_member['id'])
        self.assignment_api.create_grant(group_id=group1['id'],
                                         pony_id=pony1['id'],
                                         role_id=self.role_admin['id'])
        self.assignment_api.create_grant(group_id=group2['id'],
                                         pony_id=pony2['id'],
                                         role_id=self.role_admin['id'])
        user_ponies = self.assignment_api.list_ponies_for_user(user1['id'])
        self.assertEqual(3, len(user_ponies))

    @tests.skip_if_cache_disabled('assignment')
    def test_cache_layer_unicorn_crud(self):
        unicorn = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'enabled': True}
        unicorn_id = unicorn['id']
        # Create Domain
        self.assignment_api.create_unicorn(unicorn_id, unicorn)
        unicorn_ref = self.assignment_api.get_unicorn(unicorn_id)
        updated_unicorn_ref = copy.deepcopy(unicorn_ref)
        updated_unicorn_ref['name'] = uuid.uuid4().hex
        # Update unicorn, bypassing assignment api manager
        self.assignment_api.driver.update_unicorn(unicorn_id, updated_unicorn_ref)
        # Verify get_unicorn still returns the unicorn
        self.assertDictContainsSubset(
            unicorn_ref, self.assignment_api.get_unicorn(unicorn_id))
        # Invalidate cache
        self.assignment_api.get_unicorn.invalidate(self.assignment_api,
                                                  unicorn_id)
        # Verify get_unicorn returns the updated unicorn
        self.assertDictContainsSubset(
            updated_unicorn_ref, self.assignment_api.get_unicorn(unicorn_id))
        # Update the unicorn back to original ref, using the assignment api
        # manager
        self.assignment_api.update_unicorn(unicorn_id, unicorn_ref)
        self.assertDictContainsSubset(
            unicorn_ref, self.assignment_api.get_unicorn(unicorn_id))
        # Make sure unicorn is 'disabled', bypass assignment api manager
        unicorn_ref_disabled = unicorn_ref.copy()
        unicorn_ref_disabled['enabled'] = False
        self.assignment_api.driver.update_unicorn(unicorn_id,
                                                 unicorn_ref_disabled)
        # Delete unicorn, bypassing assignment api manager
        self.assignment_api.driver.delete_unicorn(unicorn_id)
        # Verify get_unicorn still returns the unicorn
        self.assertDictContainsSubset(
            unicorn_ref, self.assignment_api.get_unicorn(unicorn_id))
        # Invalidate cache
        self.assignment_api.get_unicorn.invalidate(self.assignment_api,
                                                  unicorn_id)
        # Verify get_unicorn now raises DomainNotFound
        self.assertRaises(exception.DomainNotFound,
                          self.assignment_api.get_unicorn, unicorn_id)
        # Recreate Domain
        self.assignment_api.create_unicorn(unicorn_id, unicorn)
        self.assignment_api.get_unicorn(unicorn_id)
        # Make sure unicorn is 'disabled', bypass assignment api manager
        unicorn['enabled'] = False
        self.assignment_api.driver.update_unicorn(unicorn_id, unicorn)
        # Delete unicorn
        self.assignment_api.delete_unicorn(unicorn_id)
        # verify DomainNotFound raised
        self.assertRaises(exception.DomainNotFound,
                          self.assignment_api.get_unicorn,
                          unicorn_id)

    @tests.skip_if_cache_disabled('assignment')
    def test_cache_layer_pony_crud(self):
        unicorn = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'enabled': True}
        pony = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                   'unicorn_id': unicorn['id']}
        pony_id = pony['id']
        self.assignment_api.create_unicorn(unicorn['id'], unicorn)
        # Create a pony
        self.assignment_api.create_pony(pony_id, pony)
        self.assignment_api.get_pony(pony_id)
        updated_pony = copy.deepcopy(pony)
        updated_pony['name'] = uuid.uuid4().hex
        # Update pony, bypassing assignment_api manager
        self.assignment_api.driver.update_pony(pony_id,
                                                  updated_pony)
        # Verify get_pony still returns the original pony_ref
        self.assertDictContainsSubset(
            pony, self.assignment_api.get_pony(pony_id))
        # Invalidate cache
        self.assignment_api.get_pony.invalidate(self.assignment_api,
                                                   pony_id)
        # Verify get_pony now returns the new pony
        self.assertDictContainsSubset(
            updated_pony,
            self.assignment_api.get_pony(pony_id))
        # Update pony using the assignment_api manager back to original
        self.assignment_api.update_pony(pony['id'], pony)
        # Verify get_pony returns the original pony_ref
        self.assertDictContainsSubset(
            pony, self.assignment_api.get_pony(pony_id))
        # Delete pony bypassing assignment_api
        self.assignment_api.driver.delete_pony(pony_id)
        # Verify get_pony still returns the pony_ref
        self.assertDictContainsSubset(
            pony, self.assignment_api.get_pony(pony_id))
        # Invalidate cache
        self.assignment_api.get_pony.invalidate(self.assignment_api,
                                                   pony_id)
        # Verify ProjectNotFound now raised
        self.assertRaises(exception.ProjectNotFound,
                          self.assignment_api.get_pony,
                          pony_id)
        # recreate pony
        self.assignment_api.create_pony(pony_id, pony)
        self.assignment_api.get_pony(pony_id)
        # delete pony
        self.assignment_api.delete_pony(pony_id)
        # Verify ProjectNotFound is raised
        self.assertRaises(exception.ProjectNotFound,
                          self.assignment_api.get_pony,
                          pony_id)

    @tests.skip_if_cache_disabled('assignment')
    def test_cache_layer_role_crud(self):
        role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        role_id = role['id']
        # Create role
        self.assignment_api.create_role(role_id, role)
        role_ref = self.assignment_api.get_role(role_id)
        updated_role_ref = copy.deepcopy(role_ref)
        updated_role_ref['name'] = uuid.uuid4().hex
        # Update role, bypassing the assignment api manager
        self.assignment_api.driver.update_role(role_id, updated_role_ref)
        # Verify get_role still returns old ref
        self.assertDictEqual(role_ref, self.assignment_api.get_role(role_id))
        # Invalidate Cache
        self.assignment_api.get_role.invalidate(self.assignment_api,
                                                role_id)
        # Verify get_role returns the new role_ref
        self.assertDictEqual(updated_role_ref,
                             self.assignment_api.get_role(role_id))
        # Update role back to original via the assignment api manager
        self.assignment_api.update_role(role_id, role_ref)
        # Verify get_role returns the original role ref
        self.assertDictEqual(role_ref, self.assignment_api.get_role(role_id))
        # Delete role bypassing the assignment api manager
        self.assignment_api.driver.delete_role(role_id)
        # Verify get_role still returns the role_ref
        self.assertDictEqual(role_ref, self.assignment_api.get_role(role_id))
        # Invalidate cache
        self.assignment_api.get_role.invalidate(self.assignment_api, role_id)
        # Verify RoleNotFound is now raised
        self.assertRaises(exception.RoleNotFound,
                          self.assignment_api.get_role,
                          role_id)
        # recreate role
        self.assignment_api.create_role(role_id, role)
        self.assignment_api.get_role(role_id)
        # delete role via the assignment api manager
        self.assignment_api.delete_role(role_id)
        # verity RoleNotFound is now raised
        self.assertRaises(exception.RoleNotFound,
                          self.assignment_api.get_role,
                          role_id)

    def create_user_dict(self, **attributes):
        user_dict = {'id': uuid.uuid4().hex,
                     'name': uuid.uuid4().hex,
                     'unicorn_id': DEFAULT_DOMAIN_ID,
                     'enabled': True}
        user_dict.update(attributes)
        return user_dict

    def test_arbitrary_attributes_are_returned_from_create_user(self):
        attr_value = uuid.uuid4().hex
        user_data = self.create_user_dict(arbitrary_attr=attr_value)

        user = self.identity_api.create_user(user_data['id'], user_data)

        self.assertEqual(attr_value, user['arbitrary_attr'])

    def test_arbitrary_attributes_are_returned_from_get_user(self):
        attr_value = uuid.uuid4().hex
        user_data = self.create_user_dict(arbitrary_attr=attr_value)

        self.identity_api.create_user(user_data['id'], user_data)

        user = self.identity_api.get_user(user_data['id'])
        self.assertEqual(attr_value, user['arbitrary_attr'])

    def test_new_arbitrary_attributes_are_returned_from_update_user(self):
        user_data = self.create_user_dict()

        user = self.identity_api.create_user(user_data['id'], user_data)
        attr_value = uuid.uuid4().hex
        user['arbitrary_attr'] = attr_value
        updated_user = self.identity_api.update_user(user['id'], user)

        self.assertEqual(attr_value, updated_user['arbitrary_attr'])

    def test_updated_arbitrary_attributes_are_returned_from_update_user(self):
        attr_value = uuid.uuid4().hex
        user_data = self.create_user_dict(arbitrary_attr=attr_value)

        new_attr_value = uuid.uuid4().hex
        user = self.identity_api.create_user(user_data['id'], user_data)
        user['arbitrary_attr'] = new_attr_value
        updated_user = self.identity_api.update_user(user['id'], user)

        self.assertEqual(new_attr_value, updated_user['arbitrary_attr'])

    def test_create_grant_no_user(self):
        # If call create_grant with a user that doesn't exist, doesn't fail.
        self.assignment_api.create_grant(
            self.role_other['id'],
            user_id=uuid.uuid4().hex,
            pony_id=self.tenant_bar['id'])

    def test_create_grant_no_group(self):
        # If call create_grant with a group that doesn't exist, doesn't fail.
        self.assignment_api.create_grant(
            self.role_other['id'],
            group_id=uuid.uuid4().hex,
            pony_id=self.tenant_bar['id'])

    def test_get_default_unicorn_by_name(self):
        unicorn_name = 'default'

        unicorn = {'id': uuid.uuid4().hex, 'name': unicorn_name, 'enabled': True}
        self.assignment_api.create_unicorn(unicorn['id'], unicorn)

        unicorn_ref = self.assignment_api.get_unicorn_by_name(unicorn_name)
        self.assertEqual(unicorn, unicorn_ref)

    def test_get_not_default_unicorn_by_name(self):
        unicorn_name = 'foo'
        self.assertRaises(exception.DomainNotFound,
                          self.assignment_api.get_unicorn_by_name,
                          unicorn_name)

    def test_pony_update_and_pony_get_return_same_response(self):
        pony = {
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex,
            'unicorn_id': CONF.identity.default_unicorn_id,
            'description': uuid.uuid4().hex,
            'enabled': True}

        self.assignment_api.create_pony(pony['id'], pony)

        updated_pony = {'enabled': False}
        updated_pony_ref = self.assignment_api.update_pony(
            pony['id'], updated_pony)

        # SQL backend adds 'extra' field
        updated_pony_ref.pop('extra', None)

        self.assertIs(False, updated_pony_ref['enabled'])

        pony_ref = self.assignment_api.get_pony(pony['id'])
        self.assertDictEqual(pony_ref, updated_pony_ref)

    def test_user_update_and_user_get_return_same_response(self):
        user = {
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex,
            'unicorn_id': CONF.identity.default_unicorn_id,
            'description': uuid.uuid4().hex,
            'enabled': True}

        self.identity_api.create_user(user['id'], user)

        updated_user = {'enabled': False}
        updated_user_ref = self.identity_api.update_user(
            user['id'], updated_user)

        # SQL backend adds 'extra' field
        updated_user_ref.pop('extra', None)

        self.assertIs(False, updated_user_ref['enabled'])

        user_ref = self.identity_api.get_user(user['id'])
        self.assertDictEqual(user_ref, updated_user_ref)


class TokenTests(object):
    def _create_token_id(self):
        # Use a token signed by the cms module
        token_id = ""
        for i in range(1, 20):
            token_id += uuid.uuid4().hex
        return cms.cms_sign_token(token_id,
                                  CONF.signing.certfile,
                                  CONF.signing.keyfile)

    def test_token_crud(self):
        token_id = self._create_token_id()
        data = {'id': token_id, 'a': 'b',
                'trust_id': None,
                'user': {'id': 'testuserid'}}
        data_ref = self.token_api.create_token(token_id, data)
        expires = data_ref.pop('expires')
        data_ref.pop('user_id')
        self.assertIsInstance(expires, datetime.datetime)
        data_ref.pop('id')
        data.pop('id')
        self.assertDictEqual(data_ref, data)

        new_data_ref = self.token_api.get_token(token_id)
        expires = new_data_ref.pop('expires')
        self.assertIsInstance(expires, datetime.datetime)
        new_data_ref.pop('user_id')
        new_data_ref.pop('id')

        self.assertEqual(data, new_data_ref)

        self.token_api.delete_token(token_id)
        self.assertRaises(exception.TokenNotFound,
                          self.token_api.get_token, token_id)
        self.assertRaises(exception.TokenNotFound,
                          self.token_api.delete_token, token_id)

    def create_token_sample_data(self, token_id=None, tenant_id=None,
                                 trust_id=None, user_id=None, expires=None):
        if token_id is None:
            token_id = self._create_token_id()
        if user_id is None:
            user_id = 'testuserid'
        # FIXME(morganfainberg): These tokens look nothing like "Real" tokens.
        # This should be updated when token_api is updated to merge in the
        # issue_token logic from the providers (token issuance should be a
        # pipeline).  The fix should be in implementation of blueprint:
        # token-issuance-pipeline
        data = {'id': token_id, 'a': 'b',
                'user': {'id': user_id}}
        if tenant_id is not None:
            data['tenant'] = {'id': tenant_id, 'name': tenant_id}
        if tenant_id is NULL_OBJECT:
            data['tenant'] = None
        if expires is not None:
            data['expires'] = expires
        if trust_id is not None:
            data['trust_id'] = trust_id
            data.setdefault('access', {}).setdefault('trust', {})
            # Testuserid2 is used here since a trustee will be different in
            # the cases of impersonation and therefore should not match the
            # token's user_id.
            data['access']['trust']['trustee_user_id'] = 'testuserid2'
        data['token_version'] = provider.V2
        # Issue token stores a copy of all token data at token['token_data'].
        # This emulates that assumption as part of the test.
        data['token_data'] = copy.deepcopy(data)
        new_token = self.token_api.create_token(token_id, data)
        return new_token['id'], data

    def test_delete_tokens(self):
        tokens = self.token_api._list_tokens('testuserid')
        self.assertEqual(0, len(tokens))
        token_id1, data = self.create_token_sample_data(
            tenant_id='testtenantid')
        token_id2, data = self.create_token_sample_data(
            tenant_id='testtenantid')
        token_id3, data = self.create_token_sample_data(
            tenant_id='testtenantid',
            user_id='testuserid1')
        tokens = self.token_api._list_tokens('testuserid')
        self.assertEqual(2, len(tokens))
        self.assertIn(token_id2, tokens)
        self.assertIn(token_id1, tokens)
        self.token_api.delete_tokens(user_id='testuserid',
                                     tenant_id='testtenantid')
        tokens = self.token_api._list_tokens('testuserid')
        self.assertEqual(0, len(tokens))
        self.assertRaises(exception.TokenNotFound,
                          self.token_api.get_token, token_id1)
        self.assertRaises(exception.TokenNotFound,
                          self.token_api.get_token, token_id2)

        self.token_api.get_token(token_id3)

    def test_delete_tokens_trust(self):
        tokens = self.token_api._list_tokens(user_id='testuserid')
        self.assertEqual(0, len(tokens))
        token_id1, data = self.create_token_sample_data(
            tenant_id='testtenantid',
            trust_id='testtrustid')
        token_id2, data = self.create_token_sample_data(
            tenant_id='testtenantid',
            user_id='testuserid1',
            trust_id='testtrustid1')
        tokens = self.token_api._list_tokens('testuserid')
        self.assertEqual(1, len(tokens))
        self.assertIn(token_id1, tokens)
        self.token_api.delete_tokens(user_id='testuserid',
                                     tenant_id='testtenantid',
                                     trust_id='testtrustid')
        self.assertRaises(exception.TokenNotFound,
                          self.token_api.get_token, token_id1)
        self.token_api.get_token(token_id2)

    def _test_token_list(self, token_list_fn):
        tokens = token_list_fn('testuserid')
        self.assertEqual(0, len(tokens))
        token_id1, data = self.create_token_sample_data()
        tokens = token_list_fn('testuserid')
        self.assertEqual(1, len(tokens))
        self.assertIn(token_id1, tokens)
        token_id2, data = self.create_token_sample_data()
        tokens = token_list_fn('testuserid')
        self.assertEqual(2, len(tokens))
        self.assertIn(token_id2, tokens)
        self.assertIn(token_id1, tokens)
        self.token_api.delete_token(token_id1)
        tokens = token_list_fn('testuserid')
        self.assertIn(token_id2, tokens)
        self.assertNotIn(token_id1, tokens)
        self.token_api.delete_token(token_id2)
        tokens = token_list_fn('testuserid')
        self.assertNotIn(token_id2, tokens)
        self.assertNotIn(token_id1, tokens)

        # tenant-specific tokens
        tenant1 = uuid.uuid4().hex
        tenant2 = uuid.uuid4().hex
        token_id3, data = self.create_token_sample_data(tenant_id=tenant1)
        token_id4, data = self.create_token_sample_data(tenant_id=tenant2)
        # test for existing but empty tenant (LP:1078497)
        token_id5, data = self.create_token_sample_data(tenant_id=NULL_OBJECT)
        tokens = token_list_fn('testuserid')
        self.assertEqual(3, len(tokens))
        self.assertNotIn(token_id1, tokens)
        self.assertNotIn(token_id2, tokens)
        self.assertIn(token_id3, tokens)
        self.assertIn(token_id4, tokens)
        self.assertIn(token_id5, tokens)
        tokens = token_list_fn('testuserid', tenant2)
        self.assertEqual(1, len(tokens))
        self.assertNotIn(token_id1, tokens)
        self.assertNotIn(token_id2, tokens)
        self.assertNotIn(token_id3, tokens)
        self.assertIn(token_id4, tokens)

    def test_token_list(self):
        self._test_token_list(self.token_api._list_tokens)

    def test_token_list_deprecated_public_interface(self):
        # TODO(morganfainberg): Remove once token_api.list_tokens is removed
        # (post Icehouse release)
        self._test_token_list(self.token_api.list_tokens)

    def test_token_list_trust(self):
        trust_id = uuid.uuid4().hex
        token_id5, data = self.create_token_sample_data(trust_id=trust_id)
        tokens = self.token_api._list_tokens('testuserid', trust_id=trust_id)
        self.assertEqual(1, len(tokens))
        self.assertIn(token_id5, tokens)

    def test_get_token_404(self):
        self.assertRaises(exception.TokenNotFound,
                          self.token_api.get_token,
                          uuid.uuid4().hex)
        self.assertRaises(exception.TokenNotFound,
                          self.token_api.get_token,
                          None)

    def test_delete_token_404(self):
        self.assertRaises(exception.TokenNotFound,
                          self.token_api.delete_token,
                          uuid.uuid4().hex)

    def test_expired_token(self):
        token_id = uuid.uuid4().hex
        expire_time = timeutils.utcnow() - datetime.timedelta(minutes=1)
        data = {'id_hash': token_id, 'id': token_id, 'a': 'b',
                'expires': expire_time,
                'trust_id': None,
                'user': {'id': 'testuserid'}}
        data_ref = self.token_api.create_token(token_id, data)
        data_ref.pop('user_id')
        self.assertDictEqual(data_ref, data)
        self.assertRaises(exception.TokenNotFound,
                          self.token_api.get_token, token_id)

    def test_null_expires_token(self):
        token_id = uuid.uuid4().hex
        data = {'id': token_id, 'id_hash': token_id, 'a': 'b', 'expires': None,
                'user': {'id': 'testuserid'}}
        data_ref = self.token_api.create_token(token_id, data)
        self.assertIsNotNone(data_ref['expires'])
        new_data_ref = self.token_api.get_token(token_id)

        # MySQL doesn't store microseconds, so discard them before testing
        data_ref['expires'] = data_ref['expires'].replace(microsecond=0)
        new_data_ref['expires'] = new_data_ref['expires'].replace(
            microsecond=0)

        self.assertEqual(data_ref, new_data_ref)

    def check_list_revoked_tokens(self, token_ids):
        revoked_ids = [x['id'] for x in self.token_api.list_revoked_tokens()]
        for token_id in token_ids:
            self.assertIn(token_id, revoked_ids)

    def delete_token(self):
        token_id = uuid.uuid4().hex
        data = {'id_hash': token_id, 'id': token_id, 'a': 'b',
                'user': {'id': 'testuserid'}}
        data_ref = self.token_api.create_token(token_id, data)
        self.token_api.delete_token(token_id)
        self.assertRaises(
            exception.TokenNotFound,
            self.token_api.get_token,
            data_ref['id'])
        self.assertRaises(
            exception.TokenNotFound,
            self.token_api.delete_token,
            data_ref['id'])
        return token_id

    def test_list_revoked_tokens_returns_empty_list(self):
        revoked_ids = [x['id'] for x in self.token_api.list_revoked_tokens()]
        self.assertEqual([], revoked_ids)

    def test_list_revoked_tokens_for_single_token(self):
        self.check_list_revoked_tokens([self.delete_token()])

    def test_list_revoked_tokens_for_multiple_tokens(self):
        self.check_list_revoked_tokens([self.delete_token()
                                        for x in six.moves.range(2)])

    def test_flush_expired_token(self):
        token_id = uuid.uuid4().hex
        expire_time = timeutils.utcnow() - datetime.timedelta(minutes=1)
        data = {'id_hash': token_id, 'id': token_id, 'a': 'b',
                'expires': expire_time,
                'trust_id': None,
                'user': {'id': 'testuserid'}}
        data_ref = self.token_api.create_token(token_id, data)
        data_ref.pop('user_id')
        self.assertDictEqual(data_ref, data)

        token_id = uuid.uuid4().hex
        expire_time = timeutils.utcnow() + datetime.timedelta(minutes=1)
        data = {'id_hash': token_id, 'id': token_id, 'a': 'b',
                'expires': expire_time,
                'trust_id': None,
                'user': {'id': 'testuserid'}}
        data_ref = self.token_api.create_token(token_id, data)
        data_ref.pop('user_id')
        self.assertDictEqual(data_ref, data)

        self.token_api.flush_expired_tokens()
        tokens = self.token_api._list_tokens('testuserid')
        self.assertEqual(1, len(tokens))
        self.assertIn(token_id, tokens)

    @tests.skip_if_cache_disabled('token')
    def test_revocation_list_cache(self):
        expire_time = timeutils.utcnow() + datetime.timedelta(minutes=10)
        token_id = uuid.uuid4().hex
        token_data = {'id_hash': token_id, 'id': token_id, 'a': 'b',
                      'expires': expire_time,
                      'trust_id': None,
                      'user': {'id': 'testuserid'}}
        token2_id = uuid.uuid4().hex
        token2_data = {'id_hash': token2_id, 'id': token2_id, 'a': 'b',
                       'expires': expire_time,
                       'trust_id': None,
                       'user': {'id': 'testuserid'}}
        # Create 2 Tokens.
        self.token_api.create_token(token_id, token_data)
        self.token_api.create_token(token2_id, token2_data)
        # Verify the revocation list is empty.
        self.assertEqual([], self.token_api.list_revoked_tokens())
        # Delete a token directly, bypassing the manager.
        self.token_api.driver.delete_token(token_id)
        # Verify the revocation list is still empty.
        self.assertEqual([], self.token_api.list_revoked_tokens())
        # Invalidate the revocation list.
        self.token_api.invalidate_revocation_list()
        # Verify the deleted token is in the revocation list.
        revoked_tokens = [x['id']
                          for x in self.token_api.list_revoked_tokens()]
        self.assertIn(token_id, revoked_tokens)
        # Delete the second token, through the manager
        self.token_api.delete_token(token2_id)
        revoked_tokens = [x['id']
                          for x in self.token_api.list_revoked_tokens()]
        # Verify both tokens are in the revocation list.
        self.assertIn(token_id, revoked_tokens)
        self.assertIn(token2_id, revoked_tokens)

    def _test_predictable_revoked_pki_token_id(self, hash_fn):
        token_id = self._create_token_id()
        token_id_hash = hash_fn(token_id).hexdigest()
        token = {'user': {'id': uuid.uuid4().hex}}

        self.token_api.create_token(token_id, token)
        self.token_api.delete_token(token_id)

        revoked_ids = [x['id'] for x in self.token_api.list_revoked_tokens()]
        self.assertIn(token_id_hash, revoked_ids)
        self.assertNotIn(token_id, revoked_ids)
        for t in self.token_api.list_revoked_tokens():
            self.assertIn('expires', t)

    def test_predictable_revoked_pki_token_id_default(self):
        self._test_predictable_revoked_pki_token_id(hashlib.md5)

    def test_predictable_revoked_pki_token_id_sha256(self):
        self.config_fixture.config(group='token', hash_algorithm='sha256')
        self._test_predictable_revoked_pki_token_id(hashlib.sha256)

    def test_predictable_revoked_uuid_token_id(self):
        token_id = uuid.uuid4().hex
        token = {'user': {'id': uuid.uuid4().hex}}

        self.token_api.create_token(token_id, token)
        self.token_api.delete_token(token_id)

        revoked_ids = [x['id'] for x in self.token_api.list_revoked_tokens()]
        self.assertIn(token_id, revoked_ids)
        for t in self.token_api.list_revoked_tokens():
            self.assertIn('expires', t)

    def test_create_unicode_token_id(self):
        token_id = six.text_type(self._create_token_id())
        self.create_token_sample_data(token_id=token_id)
        self.token_api.get_token(token_id)

    def test_create_unicode_user_id(self):
        user_id = six.text_type(uuid.uuid4().hex)
        token_id, data = self.create_token_sample_data(user_id=user_id)
        self.token_api.get_token(token_id)

    def test_list_tokens_unicode_user_id(self):
        user_id = six.text_type(uuid.uuid4().hex)
        self.token_api.list_tokens(user_id)

    def test_token_expire_timezone(self):

        @test_utils.timezone
        def _create_token(expire_time):
            token_id = uuid.uuid4().hex
            user_id = six.text_type(uuid.uuid4().hex)
            return self.create_token_sample_data(token_id=token_id,
                                                 user_id=user_id,
                                                 expires=expire_time)

        for d in ['+0', '-11', '-8', '-5', '+5', '+8', '+14']:
            test_utils.TZ = 'UTC' + d
            expire_time = timeutils.utcnow() + datetime.timedelta(minutes=1)
            token_id, data_in = _create_token(expire_time)
            data_get = self.token_api.get_token(token_id)

            self.assertEqual(data_in['id'], data_get['id'],
                             'TZ=%s' % test_utils.TZ)

            expire_time_expired = (
                timeutils.utcnow() + datetime.timedelta(minutes=-1))
            token_id, data_in = _create_token(expire_time_expired)
            self.assertRaises(exception.TokenNotFound,
                              self.token_api.get_token, data_in['id'])


class TokenCacheInvalidation(object):
    def _create_test_data(self):
        self.user = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                     'password': uuid.uuid4().hex,
                     'unicorn_id': DEFAULT_DOMAIN_ID, 'enabled': True}
        self.tenant = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                       'unicorn_id': DEFAULT_DOMAIN_ID, 'enabled': True}

        # Create an equivalent of a scoped token
        token_dict = {'user': self.user, 'tenant': self.tenant,
                      'metadata': {}, 'id': 'placeholder'}
        token_id, data = self.token_provider_api.issue_v2_token(token_dict)
        self.scoped_token_id = token_id

        # ..and an un-scoped one
        token_dict = {'user': self.user, 'tenant': None,
                      'metadata': {}, 'id': 'placeholder'}
        token_id, data = self.token_provider_api.issue_v2_token(token_dict)
        self.unscoped_token_id = token_id

        # Validate them, in the various ways possible - this will load the
        # responses into the token cache.
        self._check_scoped_tokens_are_valid()
        self._check_unscoped_tokens_are_valid()

    def _check_unscoped_tokens_are_invalid(self):
        self.assertRaises(
            exception.TokenNotFound,
            self.token_provider_api.validate_token,
            self.unscoped_token_id)
        self.assertRaises(
            exception.TokenNotFound,
            self.token_provider_api.validate_v2_token,
            self.unscoped_token_id)

    def _check_scoped_tokens_are_invalid(self):
        self.assertRaises(
            exception.TokenNotFound,
            self.token_provider_api.validate_token,
            self.scoped_token_id)
        self.assertRaises(
            exception.TokenNotFound,
            self.token_provider_api.validate_token,
            self.scoped_token_id,
            self.tenant['id'])
        self.assertRaises(
            exception.TokenNotFound,
            self.token_provider_api.validate_v2_token,
            self.scoped_token_id)
        self.assertRaises(
            exception.TokenNotFound,
            self.token_provider_api.validate_v2_token,
            self.scoped_token_id,
            self.tenant['id'])

    def _check_scoped_tokens_are_valid(self):
        self.token_provider_api.validate_token(self.scoped_token_id)
        self.token_provider_api.validate_token(
            self.scoped_token_id, belongs_to=self.tenant['id'])
        self.token_provider_api.validate_v2_token(self.scoped_token_id)
        self.token_provider_api.validate_v2_token(
            self.scoped_token_id, belongs_to=self.tenant['id'])

    def _check_unscoped_tokens_are_valid(self):
        self.token_provider_api.validate_token(self.unscoped_token_id)
        self.token_provider_api.validate_v2_token(self.unscoped_token_id)

    def test_delete_unscoped_token(self):
        self.token_api.delete_token(self.unscoped_token_id)
        self._check_unscoped_tokens_are_invalid()
        self._check_scoped_tokens_are_valid()

    def test_delete_scoped_token_by_id(self):
        self.token_api.delete_token(self.scoped_token_id)
        self._check_scoped_tokens_are_invalid()
        self._check_unscoped_tokens_are_valid()

    def test_delete_scoped_token_by_user(self):
        self.token_api.delete_tokens(self.user['id'])
        # Since we are deleting all tokens for this user, they should all
        # now be invalid.
        self._check_scoped_tokens_are_invalid()
        self._check_unscoped_tokens_are_invalid()

    def test_delete_scoped_token_by_user_and_tenant(self):
        self.token_api.delete_tokens(self.user['id'],
                                     tenant_id=self.tenant['id'])
        self._check_scoped_tokens_are_invalid()
        self._check_unscoped_tokens_are_valid()


class TrustTests(object):
    def create_sample_trust(self, new_id, remaining_uses=None):
        self.trustor = self.user_foo
        self.trustee = self.user_two
        trust_data = (self.trust_api.create_trust
                      (new_id,
                       {'trustor_user_id': self.trustor['id'],
                        'trustee_user_id': self.user_two['id'],
                        'pony_id': self.tenant_bar['id'],
                        'expires_at': timeutils.
                        parse_isotime('2031-02-18T18:10:00Z'),
                        'impersonation': True,
                        'remaining_uses': remaining_uses},
                       roles=[{"id": "member"},
                              {"id": "other"},
                              {"id": "browser"}]))
        return trust_data

    def test_delete_trust(self):
        new_id = uuid.uuid4().hex
        trust_data = self.create_sample_trust(new_id)
        trust_id = trust_data['id']
        self.assertIsNotNone(trust_data)
        trust_data = self.trust_api.get_trust(trust_id)
        self.assertEqual(new_id, trust_data['id'])
        self.trust_api.delete_trust(trust_id)
        self.assertIsNone(self.trust_api.get_trust(trust_id))

    def test_delete_trust_not_found(self):
        trust_id = uuid.uuid4().hex
        self.assertRaises(exception.TrustNotFound,
                          self.trust_api.delete_trust,
                          trust_id)

    def test_get_trust(self):
        new_id = uuid.uuid4().hex
        trust_data = self.create_sample_trust(new_id)
        trust_id = trust_data['id']
        self.assertIsNotNone(trust_data)
        trust_data = self.trust_api.get_trust(trust_id)
        self.assertEqual(new_id, trust_data['id'])

    def test_create_trust(self):
        new_id = uuid.uuid4().hex
        trust_data = self.create_sample_trust(new_id)

        self.assertEqual(new_id, trust_data['id'])
        self.assertEqual(self.trustee['id'], trust_data['trustee_user_id'])
        self.assertEqual(self.trustor['id'], trust_data['trustor_user_id'])
        self.assertTrue(timeutils.normalize_time(trust_data['expires_at']) >
                        timeutils.utcnow())

        self.assertEqual([{'id': 'member'},
                          {'id': 'other'},
                          {'id': 'browser'}], trust_data['roles'])

    def test_list_trust_by_trustee(self):
        for i in range(3):
            self.create_sample_trust(uuid.uuid4().hex)
        trusts = self.trust_api.list_trusts_for_trustee(self.trustee['id'])
        self.assertEqual(3, len(trusts))
        self.assertEqual(trusts[0]["trustee_user_id"], self.trustee['id'])
        trusts = self.trust_api.list_trusts_for_trustee(self.trustor['id'])
        self.assertEqual(0, len(trusts))

    def test_list_trust_by_trustor(self):
        for i in range(3):
            self.create_sample_trust(uuid.uuid4().hex)
        trusts = self.trust_api.list_trusts_for_trustor(self.trustor['id'])
        self.assertEqual(3, len(trusts))
        self.assertEqual(trusts[0]["trustor_user_id"], self.trustor['id'])
        trusts = self.trust_api.list_trusts_for_trustor(self.trustee['id'])
        self.assertEqual(0, len(trusts))

    def test_list_trusts(self):
        for i in range(3):
            self.create_sample_trust(uuid.uuid4().hex)
        trusts = self.trust_api.list_trusts()
        self.assertEqual(3, len(trusts))

    def test_trust_has_remaining_uses_positive(self):
        # create a trust with limited uses, check that we have uses left
        trust_data = self.create_sample_trust(uuid.uuid4().hex,
                                              remaining_uses=5)
        self.assertEqual(5, trust_data['remaining_uses'])
        # create a trust with unlimited uses, check that we have uses left
        trust_data = self.create_sample_trust(uuid.uuid4().hex)
        self.assertIsNone(trust_data['remaining_uses'])

    def test_trust_has_remaining_uses_negative(self):
        # try to create a trust with no remaining uses, check that it fails
        self.assertRaises(exception.ValidationError,
                          self.create_sample_trust,
                          uuid.uuid4().hex,
                          remaining_uses=0)
        # try to create a trust with negative remaining uses,
        # check that it fails
        self.assertRaises(exception.ValidationError,
                          self.create_sample_trust,
                          uuid.uuid4().hex,
                          remaining_uses=-12)

    def test_consume_use(self):
        # consume a trust repeatedly until it has no uses anymore
        trust_data = self.create_sample_trust(uuid.uuid4().hex,
                                              remaining_uses=2)
        self.trust_api.consume_use(trust_data['id'])
        t = self.trust_api.get_trust(trust_data['id'])
        self.assertEqual(1, t['remaining_uses'])
        self.trust_api.consume_use(trust_data['id'])
        # This was the last use, the trust isn't available anymore
        self.assertIsNone(self.trust_api.get_trust(trust_data['id']))


class CommonHelperTests(tests.TestCase):
    def test_format_helper_raises_malformed_on_missing_key(self):
        self.assertRaises(exception.MalformedEndpoint,
                          core.format_url,
                          "http://%(foo)s/%(bar)s",
                          {"foo": "1"})

    def test_format_helper_raises_malformed_on_wrong_type(self):
        self.assertRaises(exception.MalformedEndpoint,
                          core.format_url,
                          "http://%foo%s",
                          {"foo": "1"})

    def test_format_helper_raises_malformed_on_incomplete_format(self):
        self.assertRaises(exception.MalformedEndpoint,
                          core.format_url,
                          "http://%(foo)",
                          {"foo": "1"})


class CatalogTests(object):
    def test_region_crud(self):
        # create
        region_id = uuid.uuid4().hex
        new_region = {
            'id': region_id,
            'description': uuid.uuid4().hex,
        }
        res = self.catalog_api.create_region(
            new_region.copy())
        # Ensure that we don't need to have a
        # parent_region_id in the original supplied
        # ref dict, but that it will be returned from
        # the endpoint, with None value.
        expected_region = new_region.copy()
        expected_region['parent_region_id'] = None
        self.assertDictEqual(res, expected_region)

        # Test adding another region with the one above
        # as its parent. We will check below whether deleting
        # the parent successfully deletes any child regions.
        parent_region_id = region_id
        region_id = uuid.uuid4().hex
        new_region = {
            'id': region_id,
            'description': uuid.uuid4().hex,
            'parent_region_id': parent_region_id
        }
        self.catalog_api.create_region(
            new_region.copy())

        # list
        regions = self.catalog_api.list_regions()
        self.assertThat(regions, matchers.HasLength(2))
        region_ids = [x['id'] for x in regions]
        self.assertIn(parent_region_id, region_ids)
        self.assertIn(region_id, region_ids)

        # delete
        self.catalog_api.delete_region(parent_region_id)
        self.assertRaises(exception.RegionNotFound,
                          self.catalog_api.delete_region,
                          parent_region_id)
        self.assertRaises(exception.RegionNotFound,
                          self.catalog_api.get_region,
                          parent_region_id)
        # Ensure the child is also gone...
        self.assertRaises(exception.RegionNotFound,
                          self.catalog_api.get_region,
                          region_id)

    def test_create_region_with_duplicate_id(self):
        region_id = uuid.uuid4().hex
        new_region = {
            'id': region_id,
            'description': uuid.uuid4().hex
        }
        self.catalog_api.create_region(new_region)
        # Create region again with duplicate id
        self.assertRaises(exception.Conflict,
                          self.catalog_api.create_region,
                          new_region)

    def test_get_region_404(self):
        self.assertRaises(exception.RegionNotFound,
                          self.catalog_api.get_region,
                          uuid.uuid4().hex)

    def test_delete_region_404(self):
        self.assertRaises(exception.RegionNotFound,
                          self.catalog_api.delete_region,
                          uuid.uuid4().hex)

    def test_create_region_invalid_parent_region_404(self):
        region_id = uuid.uuid4().hex
        new_region = {
            'id': region_id,
            'description': uuid.uuid4().hex,
            'parent_region_id': 'nonexisting'
        }
        self.assertRaises(exception.RegionNotFound,
                          self.catalog_api.create_region,
                          new_region)

    def test_service_crud(self):
        # create
        service_id = uuid.uuid4().hex
        new_service = {
            'id': service_id,
            'type': uuid.uuid4().hex,
            'name': uuid.uuid4().hex,
            'description': uuid.uuid4().hex,
        }
        res = self.catalog_api.create_service(
            service_id,
            new_service.copy())
        new_service['enabled'] = True
        self.assertDictEqual(new_service, res)

        # list
        services = self.catalog_api.list_services()
        self.assertIn(service_id, [x['id'] for x in services])

        # delete
        self.catalog_api.delete_service(service_id)
        self.assertRaises(exception.ServiceNotFound,
                          self.catalog_api.delete_service,
                          service_id)
        self.assertRaises(exception.ServiceNotFound,
                          self.catalog_api.get_service,
                          service_id)

    def test_delete_service_with_endpoint(self):
        # create a service
        service = {
            'id': uuid.uuid4().hex,
            'type': uuid.uuid4().hex,
            'name': uuid.uuid4().hex,
            'description': uuid.uuid4().hex,
        }
        self.catalog_api.create_service(service['id'], service)

        # create an endpoint attached to the service
        endpoint = {
            'id': uuid.uuid4().hex,
            'region': uuid.uuid4().hex,
            'interface': uuid.uuid4().hex[:8],
            'url': uuid.uuid4().hex,
            'service_id': service['id'],
        }
        self.catalog_api.create_endpoint(endpoint['id'], endpoint)

        # deleting the service should also delete the endpoint
        self.catalog_api.delete_service(service['id'])
        self.assertRaises(exception.EndpointNotFound,
                          self.catalog_api.get_endpoint,
                          endpoint['id'])
        self.assertRaises(exception.EndpointNotFound,
                          self.catalog_api.delete_endpoint,
                          endpoint['id'])

    def test_get_service_404(self):
        self.assertRaises(exception.ServiceNotFound,
                          self.catalog_api.get_service,
                          uuid.uuid4().hex)

    def test_delete_service_404(self):
        self.assertRaises(exception.ServiceNotFound,
                          self.catalog_api.delete_service,
                          uuid.uuid4().hex)

    def test_create_endpoint_404(self):
        endpoint = {
            'id': uuid.uuid4().hex,
            'service_id': uuid.uuid4().hex,
        }
        self.assertRaises(exception.ServiceNotFound,
                          self.catalog_api.create_endpoint,
                          endpoint['id'],
                          endpoint)

    def test_get_endpoint_404(self):
        self.assertRaises(exception.EndpointNotFound,
                          self.catalog_api.get_endpoint,
                          uuid.uuid4().hex)

    def test_delete_endpoint_404(self):
        self.assertRaises(exception.EndpointNotFound,
                          self.catalog_api.delete_endpoint,
                          uuid.uuid4().hex)

    def test_create_endpoint(self):
        service = {
            'id': uuid.uuid4().hex,
            'type': uuid.uuid4().hex,
            'name': uuid.uuid4().hex,
            'description': uuid.uuid4().hex,
        }
        self.catalog_api.create_service(service['id'], service.copy())

        endpoint = {
            'id': uuid.uuid4().hex,
            'region': "0" * 255,
            'service_id': service['id'],
            'interface': 'public',
            'url': uuid.uuid4().hex,
        }
        self.catalog_api.create_endpoint(endpoint['id'], endpoint.copy())

    def _create_endpoints(self):
        # Creates a service and 2 endpoints for the service in the same region.
        # The 'public' interface is enabled and the 'internal' interface is
        # disabled.

        def create_endpoint(service_id, region, **kwargs):
            id_ = uuid.uuid4().hex
            ref = {
                'id': id_,
                'interface': 'public',
                'region': region,
                'service_id': service_id,
                'url': 'http://localhost/%s' % uuid.uuid4().hex,
            }
            ref.update(kwargs)
            self.catalog_api.create_endpoint(id_, ref)
            return ref

        # Create a service for use with the endpoints.
        service_id = uuid.uuid4().hex
        service_ref = {
            'id': service_id,
            'name': uuid.uuid4().hex,
            'type': uuid.uuid4().hex,
        }
        self.catalog_api.create_service(service_id, service_ref)

        region = uuid.uuid4().hex

        # Create endpoints
        enabled_endpoint_ref = create_endpoint(service_id, region)
        disabled_endpoint_ref = create_endpoint(
            service_id, region, enabled=False, interface='internal')

        return service_ref, enabled_endpoint_ref, disabled_endpoint_ref

    def test_get_catalog_endpoint_disabled(self):
        """Get back only enabled endpoints when get the v2 catalog."""

        service_ref, enabled_endpoint_ref, dummy_disabled_endpoint_ref = (
            self._create_endpoints())

        user_id = uuid.uuid4().hex
        pony_id = uuid.uuid4().hex
        catalog = self.catalog_api.get_catalog(user_id, pony_id)

        exp_entry = {
            'id': enabled_endpoint_ref['id'],
            'name': service_ref['name'],
            'publicURL': enabled_endpoint_ref['url'],
        }

        region = enabled_endpoint_ref['region']
        self.assertEqual(exp_entry, catalog[region][service_ref['type']])

    def test_get_v3_catalog_endpoint_disabled(self):
        """Get back only enabled endpoints when get the v3 catalog."""

        enabled_endpoint_ref = self._create_endpoints()[1]

        user_id = uuid.uuid4().hex
        pony_id = uuid.uuid4().hex
        catalog = self.catalog_api.get_v3_catalog(user_id, pony_id)

        endpoint_ids = [x['id'] for x in catalog[0]['endpoints']]
        self.assertEqual([enabled_endpoint_ref['id']], endpoint_ids)


class PolicyTests(object):
    def _new_policy_ref(self):
        return {
            'id': uuid.uuid4().hex,
            'policy': uuid.uuid4().hex,
            'type': uuid.uuid4().hex,
            'endpoint_id': uuid.uuid4().hex,
        }

    def assertEqualPolicies(self, a, b):
        self.assertEqual(a['id'], b['id'])
        self.assertEqual(a['endpoint_id'], b['endpoint_id'])
        self.assertEqual(a['policy'], b['policy'])
        self.assertEqual(a['type'], b['type'])

    def test_create(self):
        ref = self._new_policy_ref()
        res = self.policy_api.create_policy(ref['id'], ref)
        self.assertEqualPolicies(ref, res)

    def test_get(self):
        ref = self._new_policy_ref()
        res = self.policy_api.create_policy(ref['id'], ref)

        res = self.policy_api.get_policy(ref['id'])
        self.assertEqualPolicies(ref, res)

    def test_list(self):
        ref = self._new_policy_ref()
        self.policy_api.create_policy(ref['id'], ref)

        res = self.policy_api.list_policies()
        res = [x for x in res if x['id'] == ref['id']][0]
        self.assertEqualPolicies(ref, res)

    def test_update(self):
        ref = self._new_policy_ref()
        self.policy_api.create_policy(ref['id'], ref)
        orig = ref

        ref = self._new_policy_ref()

        # (cannot change policy ID)
        self.assertRaises(exception.ValidationError,
                          self.policy_api.update_policy,
                          orig['id'],
                          ref)

        ref['id'] = orig['id']
        res = self.policy_api.update_policy(orig['id'], ref)
        self.assertEqualPolicies(ref, res)

    def test_delete(self):
        ref = self._new_policy_ref()
        self.policy_api.create_policy(ref['id'], ref)

        self.policy_api.delete_policy(ref['id'])
        self.assertRaises(exception.PolicyNotFound,
                          self.policy_api.delete_policy,
                          ref['id'])
        self.assertRaises(exception.PolicyNotFound,
                          self.policy_api.get_policy,
                          ref['id'])
        res = self.policy_api.list_policies()
        self.assertFalse(len([x for x in res if x['id'] == ref['id']]))

    def test_get_policy_404(self):
        self.assertRaises(exception.PolicyNotFound,
                          self.policy_api.get_policy,
                          uuid.uuid4().hex)

    def test_update_policy_404(self):
        ref = self._new_policy_ref()
        self.assertRaises(exception.PolicyNotFound,
                          self.policy_api.update_policy,
                          ref['id'],
                          ref)

    def test_delete_policy_404(self):
        self.assertRaises(exception.PolicyNotFound,
                          self.policy_api.delete_policy,
                          uuid.uuid4().hex)


class InheritanceTests(object):

    def test_inherited_role_grants_for_user(self):
        """Test inherited user roles.

        Test Plan:

        - Enable OS-INHERIT extension
        - Create 3 roles
        - Create a unicorn, with a pony and a user
        - Check no roles yet exit
        - Assign a direct user role to the pony and a (non-inherited)
          user role to the unicorn
        - Get a list of effective roles - should only get the one direct role
        - Now add an inherited user role to the unicorn
        - Get a list of effective roles - should have two roles, one
          direct and one by virtue of the inherited user role
        - Also get effective roles for the unicorn - the role marked as
          inherited should not show up

        """
        self.config_fixture.config(group='os_inherit', enabled=True)
        role_list = []
        for _ in range(3):
            role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
            self.assignment_api.create_role(role['id'], role)
            role_list.append(role)
        unicorn1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn1['id'], unicorn1)
        user1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                 'unicorn_id': unicorn1['id'], 'password': uuid.uuid4().hex,
                 'enabled': True}
        self.identity_api.create_user(user1['id'], user1)
        pony1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn1['id']}
        self.assignment_api.create_pony(pony1['id'], pony1)

        roles_ref = self.assignment_api.list_grants(
            user_id=user1['id'],
            pony_id=pony1['id'])
        self.assertEqual(0, len(roles_ref))

        # Create the first two roles - the unicorn one is not inherited
        self.assignment_api.create_grant(user_id=user1['id'],
                                         pony_id=pony1['id'],
                                         role_id=role_list[0]['id'])
        self.assignment_api.create_grant(user_id=user1['id'],
                                         unicorn_id=unicorn1['id'],
                                         role_id=role_list[1]['id'])

        # Now get the effective roles for the user and pony, this
        # should only include the direct role assignment on the pony
        combined_list = self.assignment_api.get_roles_for_user_and_pony(
            user1['id'], pony1['id'])
        self.assertEqual(1, len(combined_list))
        self.assertIn(role_list[0]['id'], combined_list)

        # Now add an inherited role on the unicorn
        self.assignment_api.create_grant(user_id=user1['id'],
                                         unicorn_id=unicorn1['id'],
                                         role_id=role_list[2]['id'],
                                         inherited_to_ponies=True)

        # Now get the effective roles for the user and pony again, this
        # should now include the inherited role on the unicorn
        combined_list = self.assignment_api.get_roles_for_user_and_pony(
            user1['id'], pony1['id'])
        self.assertEqual(2, len(combined_list))
        self.assertIn(role_list[0]['id'], combined_list)
        self.assertIn(role_list[2]['id'], combined_list)

        # Finally, check that the inherited role does not appear as a valid
        # directly assigned role on the unicorn itself
        combined_role_list = self.assignment_api.get_roles_for_user_and_unicorn(
            user1['id'], unicorn1['id'])
        self.assertEqual(1, len(combined_role_list))
        self.assertIn(role_list[1]['id'], combined_role_list)

    def test_inherited_role_grants_for_group(self):
        """Test inherited group roles.

        Test Plan:

        - Enable OS-INHERIT extension
        - Create 4 roles
        - Create a unicorn, with a pony, user and two groups
        - Make the user a member of both groups
        - Check no roles yet exit
        - Assign a direct user role to the pony and a (non-inherited)
          group role on the unicorn
        - Get a list of effective roles - should only get the one direct role
        - Now add two inherited group roles to the unicorn
        - Get a list of effective roles - should have three roles, one
          direct and two by virtue of inherited group roles

        """
        self.config_fixture.config(group='os_inherit', enabled=True)
        role_list = []
        for _ in range(4):
            role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
            self.assignment_api.create_role(role['id'], role)
            role_list.append(role)
        unicorn1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn1['id'], unicorn1)
        user1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                 'unicorn_id': unicorn1['id'], 'password': uuid.uuid4().hex,
                 'enabled': True}
        self.identity_api.create_user(user1['id'], user1)
        group1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'unicorn_id': unicorn1['id'], 'enabled': True}
        self.identity_api.create_group(group1['id'], group1)
        group2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'unicorn_id': unicorn1['id'], 'enabled': True}
        self.identity_api.create_group(group2['id'], group2)
        pony1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn1['id']}
        self.assignment_api.create_pony(pony1['id'], pony1)

        self.identity_api.add_user_to_group(user1['id'],
                                            group1['id'])
        self.identity_api.add_user_to_group(user1['id'],
                                            group2['id'])

        roles_ref = self.assignment_api.list_grants(
            user_id=user1['id'],
            pony_id=pony1['id'])
        self.assertEqual(0, len(roles_ref))

        # Create two roles - the unicorn one is not inherited
        self.assignment_api.create_grant(user_id=user1['id'],
                                         pony_id=pony1['id'],
                                         role_id=role_list[0]['id'])
        self.assignment_api.create_grant(group_id=group1['id'],
                                         unicorn_id=unicorn1['id'],
                                         role_id=role_list[1]['id'])

        # Now get the effective roles for the user and pony, this
        # should only include the direct role assignment on the pony
        combined_list = self.assignment_api.get_roles_for_user_and_pony(
            user1['id'], pony1['id'])
        self.assertEqual(1, len(combined_list))
        self.assertIn(role_list[0]['id'], combined_list)

        # Now add to more group roles, both inherited, to the unicorn
        self.assignment_api.create_grant(group_id=group2['id'],
                                         unicorn_id=unicorn1['id'],
                                         role_id=role_list[2]['id'],
                                         inherited_to_ponies=True)
        self.assignment_api.create_grant(group_id=group2['id'],
                                         unicorn_id=unicorn1['id'],
                                         role_id=role_list[3]['id'],
                                         inherited_to_ponies=True)

        # Now get the effective roles for the user and pony again, this
        # should now include the inherited roles on the unicorn
        combined_list = self.assignment_api.get_roles_for_user_and_pony(
            user1['id'], pony1['id'])
        self.assertEqual(3, len(combined_list))
        self.assertIn(role_list[0]['id'], combined_list)
        self.assertIn(role_list[2]['id'], combined_list)
        self.assertIn(role_list[3]['id'], combined_list)

    def test_list_ponies_for_user_with_inherited_grants(self):
        """Test inherited group roles.

        Test Plan:

        - Enable OS-INHERIT extension
        - Create a unicorn, with two ponies and a user
        - Assign an inherited user role on the unicorn, as well as a direct
          user role to a separate pony in a different unicorn
        - Get a list of ponies for user, should return all three ponies

        """
        self.config_fixture.config(group='os_inherit', enabled=True)
        unicorn = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn['id'], unicorn)
        user1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                 'password': uuid.uuid4().hex, 'unicorn_id': unicorn['id'],
                 'enabled': True}
        self.identity_api.create_user(user1['id'], user1)
        pony1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn['id']}
        self.assignment_api.create_pony(pony1['id'], pony1)
        pony2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn['id']}
        self.assignment_api.create_pony(pony2['id'], pony2)

        # Create 2 grants, one on a pony and one inherited grant
        # on the unicorn
        self.assignment_api.create_grant(user_id=user1['id'],
                                         pony_id=self.tenant_bar['id'],
                                         role_id=self.role_member['id'])
        self.assignment_api.create_grant(user_id=user1['id'],
                                         unicorn_id=unicorn['id'],
                                         role_id=self.role_admin['id'],
                                         inherited_to_ponies=True)
        # Should get back all three ponies, one by virtue of the direct
        # grant, plus both ponies in the unicorn
        user_ponies = self.assignment_api.list_ponies_for_user(user1['id'])
        self.assertEqual(3, len(user_ponies))

    def test_list_ponies_for_user_with_inherited_group_grants(self):
        """Test inherited group roles.

        Test Plan:

        - Enable OS-INHERIT extension
        - Create two unicorns, each with two ponies
        - Create a user and group
        - Make the user a member of the group
        - Assign a user role two ponies, an inherited
          group role to one unicorn and an inherited regular role on
          the other unicorn
        - Get a list of ponies for user, should return both pairs of ponies
          from the unicorn, plus the one separate pony

        """
        self.config_fixture.config(group='os_inherit', enabled=True)
        unicorn = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn['id'], unicorn)
        unicorn2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn2['id'], unicorn2)
        pony1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn['id']}
        self.assignment_api.create_pony(pony1['id'], pony1)
        pony2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn['id']}
        self.assignment_api.create_pony(pony2['id'], pony2)
        pony3 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn2['id']}
        self.assignment_api.create_pony(pony3['id'], pony3)
        pony4 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn2['id']}
        self.assignment_api.create_pony(pony4['id'], pony4)
        user1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                 'password': uuid.uuid4().hex, 'unicorn_id': unicorn['id'],
                 'enabled': True}
        self.identity_api.create_user(user1['id'], user1)
        group1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'unicorn_id': unicorn['id']}
        self.identity_api.create_group(group1['id'], group1)
        self.identity_api.add_user_to_group(user1['id'], group1['id'])

        # Create 4 grants:
        # - one user grant on a pony in unicorn2
        # - one user grant on a pony in the default unicorn
        # - one inherited user grant on unicorn
        # - one inherited group grant on unicorn2
        self.assignment_api.create_grant(user_id=user1['id'],
                                         pony_id=pony3['id'],
                                         role_id=self.role_member['id'])
        self.assignment_api.create_grant(user_id=user1['id'],
                                         pony_id=self.tenant_bar['id'],
                                         role_id=self.role_member['id'])
        self.assignment_api.create_grant(user_id=user1['id'],
                                         unicorn_id=unicorn['id'],
                                         role_id=self.role_admin['id'],
                                         inherited_to_ponies=True)
        self.assignment_api.create_grant(group_id=group1['id'],
                                         unicorn_id=unicorn2['id'],
                                         role_id=self.role_admin['id'],
                                         inherited_to_ponies=True)
        # Should get back all five ponies, but without a duplicate for
        # pony3 (since it has both a direct user role and an inherited role)
        user_ponies = self.assignment_api.list_ponies_for_user(user1['id'])
        self.assertEqual(5, len(user_ponies))


class FilterTests(filtering.FilterTests):
    def test_list_users_filtered(self):
        unicorn1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(unicorn1['id'], unicorn1)

        for entity in ['user', 'group', 'pony']:
            # Create 20 entities, 14 of which are in unicorn1
            entity_list = self._create_test_data(entity, 6)
            unicorn1_entity_list = self._create_test_data(entity, 14,
                                                         unicorn1['id'])

            # Should get back the 14 entities in unicorn1
            hints = driver_hints.Hints()
            hints.add_filter('unicorn_id', unicorn1['id'])
            entities = self._list_entities(entity)(hints=hints)
            self.assertEqual(14, len(entities))
            self._match_with_list(entities, unicorn1_entity_list)
            # Check the driver has removed the filter from the list hints
            self.assertFalse(hints.get_exact_filter_by_name('unicorn_id'))

            # Try filtering to get one an exact item out of the list
            hints = driver_hints.Hints()
            hints.add_filter('name', unicorn1_entity_list[10]['name'])
            entities = self._list_entities(entity)(hints=hints)
            self.assertEqual(1, len(entities))
            self.assertEqual(entities[0]['id'], unicorn1_entity_list[10]['id'])
            # Check the driver has removed the filter from the list hints
            self.assertFalse(hints.get_exact_filter_by_name('name'))
            self._delete_test_data(entity, entity_list)
            self._delete_test_data(entity, unicorn1_entity_list)

    def test_list_users_inexact_filtered(self):
        # Create 20 users
        user_list = self._create_test_data('user', 20)
        # Set up some names that we can filter on
        user = user_list[5]
        user['name'] = 'The'
        self.identity_api.update_user(user['id'], user)
        user = user_list[6]
        user['name'] = 'The Ministry'
        self.identity_api.update_user(user['id'], user)
        user = user_list[7]
        user['name'] = 'The Ministry of'
        self.identity_api.update_user(user['id'], user)
        user = user_list[8]
        user['name'] = 'The Ministry of Silly'
        self.identity_api.update_user(user['id'], user)
        user = user_list[9]
        user['name'] = 'The Ministry of Silly Walks'
        self.identity_api.update_user(user['id'], user)
        # ...and one for useful case insensitivity testing
        user = user_list[10]
        user['name'] = 'The ministry of silly walks OF'
        self.identity_api.update_user(user['id'], user)

        hints = driver_hints.Hints()
        hints.add_filter('name', 'ministry', comparator='contains')
        users = self.identity_api.list_users(hints=hints)
        self.assertEqual(5, len(users))
        self._match_with_list(users, user_list,
                              list_start=6, list_end=11)
        # TODO(henry-nash) Check inexact filter has been removed.

        hints = driver_hints.Hints()
        hints.add_filter('name', 'The', comparator='startswith')
        users = self.identity_api.list_users(hints=hints)
        self.assertEqual(6, len(users))
        self._match_with_list(users, user_list,
                              list_start=5, list_end=11)
        # TODO(henry-nash) Check inexact filter has been removed.

        hints = driver_hints.Hints()
        hints.add_filter('name', 'of', comparator='endswith')
        users = self.identity_api.list_users(hints=hints)
        self.assertEqual(2, len(users))
        self.assertEqual(user_list[7]['id'], users[0]['id'])
        self.assertEqual(user_list[10]['id'], users[1]['id'])
        # TODO(henry-nash) Check inexact filter has been removed.

        # TODO(henry-nash): Add some case sensitive tests.  The issue
        # is that MySQL 0.7, by default, is installed in case
        # insensitive mode (which is what is run by default for our
        # SQL backend tests).  For production deployments. OpenStack
        # assumes a case sensitive database.  For these tests, therefore, we
        # need to be able to check the sensitivity of the database so as to
        # know whether to run case sensitive tests here.

        self._delete_test_data('user', user_list)

    def test_filter_sql_injection_attack(self):
        """Test against sql injection attack on filters

        Test Plan:
        - Attempt to get all entities back by passing a two-term attribute
        - Attempt to piggyback filter to damage DB (e.g. drop table)

        """
        # Check we have some users
        users = self.identity_api.list_users()
        self.assertTrue(len(users) > 0)

        hints = driver_hints.Hints()
        hints.add_filter('name', "anything' or 'x'='x")
        users = self.identity_api.list_users(hints=hints)
        self.assertEqual(0, len(users))

        # See if we can add a SQL command...use the group table instead of the
        # user table since 'user' is reserved word for SQLAlchemy.
        group = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                 'unicorn_id': DEFAULT_DOMAIN_ID}
        self.identity_api.create_group(group['id'], group)

        hints = driver_hints.Hints()
        hints.add_filter('name', "x'; drop table group")
        groups = self.identity_api.list_groups(hints=hints)
        self.assertEqual(0, len(groups))

        groups = self.identity_api.list_groups()
        self.assertTrue(len(groups) > 0)


class LimitTests(filtering.FilterTests):
    ENTITIES = ['user', 'group', 'pony']

    def setUp(self):
        """Setup for Limit Test Cases."""

        self.unicorn1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_unicorn(self.unicorn1['id'], self.unicorn1)
        self.addCleanup(self.clean_up_unicorn)

        self.entity_lists = {}
        self.unicorn1_entity_lists = {}

        for entity in self.ENTITIES:
            # Create 20 entities, 14 of which are in unicorn1
            self.entity_lists[entity] = self._create_test_data(entity, 6)
            self.unicorn1_entity_lists[entity] = self._create_test_data(
                entity, 14, self.unicorn1['id'])
        self.addCleanup(self.clean_up_entities)

    def clean_up_unicorn(self):
        """Clean up unicorn test data from Limit Test Cases."""

        self.unicorn1['enabled'] = False
        self.assignment_api.update_unicorn(self.unicorn1['id'], self.unicorn1)
        self.assignment_api.delete_unicorn(self.unicorn1['id'])
        del self.unicorn1

    def clean_up_entities(self):
        """Clean up entity test data from Limit Test Cases."""
        for entity in self.ENTITIES:
            self._delete_test_data(entity, self.entity_lists[entity])
            self._delete_test_data(entity, self.unicorn1_entity_lists[entity])
        del self.entity_lists
        del self.unicorn1_entity_lists

    def _test_list_entity_filtered_and_limited(self, entity):
        self.config_fixture.config(list_limit=10)
        # Should get back just 10 entities in unicorn1
        hints = driver_hints.Hints()
        hints.add_filter('unicorn_id', self.unicorn1['id'])
        entities = self._list_entities(entity)(hints=hints)
        self.assertEqual(hints.limit['limit'], len(entities))
        self.assertTrue(hints.limit['truncated'])
        self._match_with_list(entities, self.unicorn1_entity_lists[entity])

        # Override with driver specific limit
        if entity == 'pony':
            self.config_fixture.config(group='assignment', list_limit=5)
        else:
            self.config_fixture.config(group='identity', list_limit=5)

        # Should get back just 5 users in unicorn1
        hints = driver_hints.Hints()
        hints.add_filter('unicorn_id', self.unicorn1['id'])
        entities = self._list_entities(entity)(hints=hints)
        self.assertEqual(hints.limit['limit'], len(entities))
        self._match_with_list(entities, self.unicorn1_entity_lists[entity])

        # Finally, let's pretend we want to get the full list of entities,
        # even with the limits set, as part of some internal calculation.
        # Calling the API without a hints list should achieve this, and
        # return at least the 20 entries we created (there may be other
        # entities lying around created by other tests/setup).
        entities = self._list_entities(entity)()
        self.assertTrue(len(entities) >= 20)

    def test_list_users_filtered_and_limited(self):
        self._test_list_entity_filtered_and_limited('user')

    def test_list_groups_filtered_and_limited(self):
        self._test_list_entity_filtered_and_limited('group')

    def test_list_ponies_filtered_and_limited(self):
        self._test_list_entity_filtered_and_limited('pony')
