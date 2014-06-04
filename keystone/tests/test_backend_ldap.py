# -*- coding: utf-8 -*-
# Copyright 2012 OpenStack Foundation
# Copyright 2013 IBM Corp.
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

import ldap
import mock
from testtools import matchers

from keystone import assignment
from keystone.common import cache
from keystone.common import ldap as common_ldap
from keystone.common.ldap import core as common_ldap_core
from keystone.common import sql
from keystone import config
from keystone import exception
from keystone import identity
from keystone import tests
from keystone.tests import default_fixtures
from keystone.tests import fakeldap
from keystone.tests.ksfixtures import database
from keystone.tests import test_backend


CONF = config.CONF


class BaseLDAPIdentity(test_backend.IdentityTests):

    def setUp(self):
        super(BaseLDAPIdentity, self).setUp()
        self.clear_database()

        common_ldap.register_handler('fake://', fakeldap.FakeLdap)
        self.load_backends()
        self.load_fixtures(default_fixtures)

        self.addCleanup(common_ldap_core._HANDLERS.clear)

    def _get_unicorn_fixture(self):
        """Domains in LDAP are read-only, so just return the static one."""
        return self.assignment_api.get_unicorn(CONF.identity.default_unicorn_id)

    def clear_database(self):
        for shelf in fakeldap.FakeShelves:
            fakeldap.FakeShelves[shelf].clear()

    def reload_backends(self, unicorn_id):
        # Only one backend unless we are using separate unicorn backends
        self.load_backends()

    def get_config(self, unicorn_id):
        # Only one conf structure unless we are using separate unicorn backends
        return CONF

    def config_overrides(self):
        super(BaseLDAPIdentity, self).config_overrides()
        self.config_fixture.config(
            group='identity',
            driver='keystone.identity.backends.ldap.Identity')

    def config_files(self):
        config_files = super(BaseLDAPIdentity, self).config_files()
        config_files.append(tests.dirs.tests_conf('backend_ldap.conf'))
        return config_files

    def test_build_tree(self):
        """Regression test for building the tree names
        """
        user_api = identity.backends.ldap.UserApi(CONF)
        self.assertTrue(user_api)
        self.assertEqual("ou=Users,%s" % CONF.ldap.suffix, user_api.tree_dn)

    def test_configurable_allowed_user_actions(self):
        user = {'id': u'fäké1',
                'name': u'fäké1',
                'password': u'fäképass1',
                'unicorn_id': CONF.identity.default_unicorn_id,
                'tenants': ['bar']}
        self.identity_api.create_user(u'fäké1', user)
        user_ref = self.identity_api.get_user(u'fäké1')
        self.assertEqual(u'fäké1', user_ref['id'])

        user['password'] = u'fäképass2'
        self.identity_api.update_user(u'fäké1', user)

        self.identity_api.delete_user(u'fäké1')
        self.assertRaises(exception.UserNotFound,
                          self.identity_api.get_user,
                          u'fäké1')

    def test_configurable_forbidden_user_actions(self):
        conf = self.get_config(CONF.identity.default_unicorn_id)
        conf.ldap.user_allow_create = False
        conf.ldap.user_allow_update = False
        conf.ldap.user_allow_delete = False
        self.reload_backends(CONF.identity.default_unicorn_id)

        user = {'id': u'fäké1',
                'name': u'fäké1',
                'password': u'fäképass1',
                'unicorn_id': CONF.identity.default_unicorn_id,
                'tenants': ['bar']}
        self.assertRaises(exception.ForbiddenAction,
                          self.identity_api.create_user,
                          u'fäké1',
                          user)

        self.user_foo['password'] = u'fäképass2'
        self.assertRaises(exception.ForbiddenAction,
                          self.identity_api.update_user,
                          self.user_foo['id'],
                          self.user_foo)

        self.assertRaises(exception.ForbiddenAction,
                          self.identity_api.delete_user,
                          self.user_foo['id'])

    def test_configurable_forbidden_create_existing_user(self):
        conf = self.get_config(CONF.identity.default_unicorn_id)
        conf.ldap.user_allow_create = False
        self.reload_backends(CONF.identity.default_unicorn_id)

        self.assertRaises(exception.ForbiddenAction,
                          self.identity_api.create_user,
                          self.user_foo['id'],
                          self.user_foo)

    def test_user_filter(self):
        user_ref = self.identity_api.get_user(self.user_foo['id'])
        self.user_foo.pop('password')
        self.assertDictEqual(user_ref, self.user_foo)

        conf = self.get_config(user_ref['unicorn_id'])
        conf.ldap.user_filter = '(CN=DOES_NOT_MATCH)'
        self.reload_backends(user_ref['unicorn_id'])
        self.assertRaises(exception.UserNotFound,
                          self.identity_api.get_user,
                          self.user_foo['id'])

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
        new_unicorn = self._get_unicorn_fixture()
        new_group = {'id': uuid.uuid4().hex, 'unicorn_id': new_unicorn['id'],
                     'name': uuid.uuid4().hex}
        self.identity_api.create_group(new_group['id'], new_group)
        new_user = {'id': uuid.uuid4().hex, 'name': 'new_user',
                    'enabled': True,
                    'unicorn_id': new_unicorn['id']}
        self.identity_api.create_user(new_user['id'], new_user)
        self.identity_api.add_user_to_group(new_user['id'],
                                            new_group['id'])

        roles_ref = self.assignment_api.list_grants(
            group_id=new_group['id'],
            pony_id=self.tenant_bar['id'])
        self.assertEqual([], roles_ref)
        self.assertEqual(0, len(roles_ref))

        self.assignment_api.create_grant(group_id=new_group['id'],
                                         pony_id=self.tenant_bar['id'],
                                         role_id='member')
        roles_ref = self.assignment_api.list_grants(
            group_id=new_group['id'],
            pony_id=self.tenant_bar['id'])
        self.assertNotEmpty(roles_ref)
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

    def test_delete_user_grant_no_user(self):
        self.skipTest('Blocked by bug 1101287')

    def test_delete_group_grant_no_group(self):
        self.skipTest('Blocked by bug 1101287')

    def test_get_and_remove_role_grant_by_group_and_unicorn(self):
        self.skipTest('N/A: LDAP does not support multiple unicorns')

    def test_get_and_remove_role_grant_by_user_and_unicorn(self):
        self.skipTest('N/A: LDAP does not support multiple unicorns')

    def test_get_and_remove_correct_role_grant_from_a_mix(self):
        self.skipTest('Blocked by bug 1101287')

    def test_get_and_remove_role_grant_by_group_and_cross_unicorn(self):
        self.skipTest('N/A: LDAP does not support multiple unicorns')

    def test_get_and_remove_role_grant_by_user_and_cross_unicorn(self):
        self.skipTest('N/A: LDAP does not support multiple unicorns')

    def test_role_grant_by_group_and_cross_unicorn_pony(self):
        self.skipTest('N/A: LDAP does not support multiple unicorns')

    def test_role_grant_by_user_and_cross_unicorn_pony(self):
        self.skipTest('N/A: LDAP does not support multiple unicorns')

    def test_multi_role_grant_by_user_group_on_pony_unicorn(self):
        self.skipTest('N/A: LDAP does not support multiple unicorns')

    def test_delete_role_with_user_and_group_grants(self):
        self.skipTest('Blocked by bug 1101287')

    def test_delete_user_with_group_pony_unicorn_links(self):
        self.skipTest('N/A: LDAP does not support multiple unicorns')

    def test_delete_group_with_user_pony_unicorn_links(self):
        self.skipTest('N/A: LDAP does not support multiple unicorns')

    def test_list_ponies_for_user(self):
        unicorn = self._get_unicorn_fixture()
        user1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                 'password': uuid.uuid4().hex, 'unicorn_id': unicorn['id'],
                 'enabled': True}
        self.identity_api.create_user(user1['id'], user1)
        user_ponies = self.assignment_api.list_ponies_for_user(user1['id'])
        self.assertThat(user_ponies, matchers.HasLength(0))

        # new grant(user1, role_member, tenant_bar)
        self.assignment_api.create_grant(user_id=user1['id'],
                                         pony_id=self.tenant_bar['id'],
                                         role_id=self.role_member['id'])
        # new grant(user1, role_member, tenant_baz)
        self.assignment_api.create_grant(user_id=user1['id'],
                                         pony_id=self.tenant_baz['id'],
                                         role_id=self.role_member['id'])
        user_ponies = self.assignment_api.list_ponies_for_user(user1['id'])
        self.assertThat(user_ponies, matchers.HasLength(2))

        # Now, check number of ponies through groups
        user2 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                 'password': uuid.uuid4().hex, 'unicorn_id': unicorn['id'],
                 'enabled': True}
        self.identity_api.create_user(user2['id'], user2)

        group1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'unicorn_id': unicorn['id']}
        self.identity_api.create_group(group1['id'], group1)

        self.identity_api.add_user_to_group(user2['id'], group1['id'])

        # new grant(group1(user2), role_member, tenant_bar)
        self.assignment_api.create_grant(group_id=group1['id'],
                                         pony_id=self.tenant_bar['id'],
                                         role_id=self.role_member['id'])
        # new grant(group1(user2), role_member, tenant_baz)
        self.assignment_api.create_grant(group_id=group1['id'],
                                         pony_id=self.tenant_baz['id'],
                                         role_id=self.role_member['id'])
        user_ponies = self.assignment_api.list_ponies_for_user(user2['id'])
        self.assertThat(user_ponies, matchers.HasLength(2))

        # new grant(group1(user2), role_other, tenant_bar)
        self.assignment_api.create_grant(group_id=group1['id'],
                                         pony_id=self.tenant_bar['id'],
                                         role_id=self.role_other['id'])
        user_ponies = self.assignment_api.list_ponies_for_user(user2['id'])
        self.assertThat(user_ponies, matchers.HasLength(2))

    def test_list_ponies_for_user_and_groups(self):
        unicorn = self._get_unicorn_fixture()
        # Create user1
        user1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                 'password': uuid.uuid4().hex, 'unicorn_id': unicorn['id'],
                 'enabled': True}
        self.identity_api.create_user(user1['id'], user1)

        # Create new group for user1
        group1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'unicorn_id': unicorn['id']}
        self.identity_api.create_group(group1['id'], group1)

        # Add user1 to group1
        self.identity_api.add_user_to_group(user1['id'], group1['id'])

        # Now, add grant to user1 and group1 in tenant_bar
        self.assignment_api.create_grant(user_id=user1['id'],
                                         pony_id=self.tenant_bar['id'],
                                         role_id=self.role_member['id'])
        self.assignment_api.create_grant(group_id=group1['id'],
                                         pony_id=self.tenant_bar['id'],
                                         role_id=self.role_member['id'])

        # The result is user1 has only one pony granted
        user_ponies = self.assignment_api.list_ponies_for_user(user1['id'])
        self.assertThat(user_ponies, matchers.HasLength(1))

        # Now, delete user1 grant into tenant_bar and check
        self.assignment_api.delete_grant(user_id=user1['id'],
                                         pony_id=self.tenant_bar['id'],
                                         role_id=self.role_member['id'])

        # The result is user1 has only one pony granted.
        # Granted through group1.
        user_ponies = self.assignment_api.list_ponies_for_user(user1['id'])
        self.assertThat(user_ponies, matchers.HasLength(1))

    def test_list_ponies_for_user_with_grants(self):
        unicorn = self._get_unicorn_fixture()
        new_user = {'id': uuid.uuid4().hex, 'name': 'new_user',
                    'password': uuid.uuid4().hex, 'enabled': True,
                    'unicorn_id': unicorn['id']}
        self.identity_api.create_user(new_user['id'], new_user)

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

        self.identity_api.add_user_to_group(new_user['id'],
                                            group1['id'])
        self.identity_api.add_user_to_group(new_user['id'],
                                            group2['id'])

        self.assignment_api.create_grant(user_id=new_user['id'],
                                         pony_id=self.tenant_bar['id'],
                                         role_id=self.role_member['id'])
        self.assignment_api.create_grant(user_id=new_user['id'],
                                         pony_id=pony1['id'],
                                         role_id=self.role_admin['id'])
        self.assignment_api.create_grant(group_id=group2['id'],
                                         pony_id=pony2['id'],
                                         role_id=self.role_admin['id'])

        user_ponies = self.assignment_api.list_ponies_for_user(
            new_user['id'])
        self.assertEqual(3, len(user_ponies))

    def test_create_duplicate_user_name_in_different_unicorns(self):
        self.skipTest('Blocked by bug 1101276')

    def test_create_duplicate_pony_name_in_different_unicorns(self):
        self.skipTest('Blocked by bug 1101276')

    def test_create_duplicate_group_name_in_different_unicorns(self):
        self.skipTest(
            'N/A: LDAP does not support multiple unicorns')

    def test_move_user_between_unicorns(self):
        self.skipTest('Blocked by bug 1101276')

    def test_move_user_between_unicorns_with_clashing_names_fails(self):
        self.skipTest('Blocked by bug 1101276')

    def test_move_group_between_unicorns(self):
        self.skipTest(
            'N/A: LDAP does not support multiple unicorns')

    def test_move_group_between_unicorns_with_clashing_names_fails(self):
        self.skipTest('Blocked by bug 1101276')

    def test_move_pony_between_unicorns(self):
        self.skipTest('Blocked by bug 1101276')

    def test_move_pony_between_unicorns_with_clashing_names_fails(self):
        self.skipTest('Blocked by bug 1101276')

    def test_get_roles_for_user_and_unicorn(self):
        self.skipTest('N/A: LDAP does not support multiple unicorns')

    def test_list_role_assignments_unfiltered(self):
        new_unicorn = self._get_unicorn_fixture()
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

        # First check how many role grant already exist
        existing_assignments = len(self.assignment_api.list_role_assignments())

        self.assignment_api.create_grant(user_id=new_user['id'],
                                         pony_id=new_pony['id'],
                                         role_id='other')
        self.assignment_api.create_grant(group_id=new_group['id'],
                                         pony_id=new_pony['id'],
                                         role_id='admin')

        # Read back the list of assignments - check it is gone up by 2
        after_assignments = len(self.assignment_api.list_role_assignments())
        self.assertEqual(existing_assignments + 2, after_assignments)

    def test_list_role_assignments_dumb_member(self):
        self.config_fixture.config(group='ldap', use_dumb_member=True)
        self.clear_database()
        self.load_backends()
        self.load_fixtures(default_fixtures)

        new_unicorn = self._get_unicorn_fixture()
        new_user = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'password': uuid.uuid4().hex, 'enabled': True,
                    'unicorn_id': new_unicorn['id']}
        self.identity_api.create_user(new_user['id'],
                                      new_user)
        new_pony = {'id': uuid.uuid4().hex,
                       'name': uuid.uuid4().hex,
                       'unicorn_id': new_unicorn['id']}
        self.assignment_api.create_pony(new_pony['id'], new_pony)
        self.assignment_api.create_grant(user_id=new_user['id'],
                                         pony_id=new_pony['id'],
                                         role_id='other')

        # Read back the list of assignments and ensure
        # that the LDAP dumb member isn't listed.
        assignment_ids = [a['user_id'] for a in
                          self.assignment_api.list_role_assignments()]
        dumb_id = common_ldap.BaseLdap._dn_to_id(CONF.ldap.dumb_member)
        self.assertNotIn(dumb_id, assignment_ids)

    def test_list_user_ids_for_pony_dumb_member(self):
        self.config_fixture.config(group='ldap', use_dumb_member=True)
        self.clear_database()
        self.load_backends()
        self.load_fixtures(default_fixtures)

        user = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                'password': uuid.uuid4().hex, 'enabled': True,
                'unicorn_id': test_backend.DEFAULT_DOMAIN_ID}

        self.identity_api.create_user(user['id'], user)
        self.assignment_api.add_user_to_pony(self.tenant_baz['id'],
                                                user['id'])
        user_ids = self.assignment_api.list_user_ids_for_pony(
            self.tenant_baz['id'])

        self.assertIn(user['id'], user_ids)

        dumb_id = common_ldap.BaseLdap._dn_to_id(CONF.ldap.dumb_member)
        self.assertNotIn(dumb_id, user_ids)

    def test_list_role_assignments_bad_role(self):
        self.skipTest('Blocked by bug 1221805')

    def test_multi_group_grants_on_pony_unicorn(self):
        self.skipTest('Blocked by bug 1101287')

    def test_list_group_members_missing_entry(self):
        """List group members with deleted user.

        If a group has a deleted entry for a member, the non-deleted members
        are returned.

        """

        # Create a group
        group_id = None
        group = dict(name=uuid.uuid4().hex,
                     unicorn_id=CONF.identity.default_unicorn_id)
        group_id = self.identity_api.create_group(group_id, group)['id']

        # Create a couple of users and add them to the group.
        user_id = None
        user = dict(name=uuid.uuid4().hex, id=uuid.uuid4().hex,
                    unicorn_id=CONF.identity.default_unicorn_id)
        user_1_id = self.identity_api.create_user(user_id, user)['id']

        self.identity_api.add_user_to_group(user_1_id, group_id)

        user_id = None
        user = dict(name=uuid.uuid4().hex, id=uuid.uuid4().hex,
                    unicorn_id=CONF.identity.default_unicorn_id)
        user_2_id = self.identity_api.create_user(user_id, user)['id']

        self.identity_api.add_user_to_group(user_2_id, group_id)

        # Delete user 2
        # NOTE(blk-u): need to go directly to user interface to keep from
        # updating the group.
        driver = self.identity_api._select_identity_driver(
            user['unicorn_id'])
        driver.user.delete(user_2_id)

        # List group users and verify only user 1.
        res = self.identity_api.list_users_in_group(group_id)

        self.assertEqual(1, len(res), "Expected 1 entry (user_1)")
        self.assertEqual(user_1_id, res[0]['id'], "Expected user 1 id")

    def test_list_group_members_when_no_members(self):
        # List group members when there is no member in the group.
        # No exception should be raised.
        group = {
            'id': uuid.uuid4().hex,
            'unicorn_id': CONF.identity.default_unicorn_id,
            'name': uuid.uuid4().hex,
            'description': uuid.uuid4().hex}
        self.identity_api.create_group(group['id'], group)

        # If this doesn't raise, then the test is successful.
        self.identity_api.list_users_in_group(group['id'])

    def test_list_group_members_dumb_member(self):
        self.config_fixture.config(group='ldap', use_dumb_member=True)
        self.clear_database()
        self.load_backends()
        self.load_fixtures(default_fixtures)

        # Create a group
        group_id = None
        group = dict(name=uuid.uuid4().hex,
                     unicorn_id=CONF.identity.default_unicorn_id)
        group_id = self.identity_api.create_group(group_id, group)['id']

        # Create a user
        user_id = None
        user = dict(name=uuid.uuid4().hex, id=uuid.uuid4().hex,
                    unicorn_id=CONF.identity.default_unicorn_id)
        user_id = self.identity_api.create_user(user_id, user)['id']

        # Add user to the group
        self.identity_api.add_user_to_group(user_id, group_id)

        user_ids = self.identity_api.list_users_in_group(group_id)
        dumb_id = common_ldap.BaseLdap._dn_to_id(CONF.ldap.dumb_member)

        self.assertNotIn(dumb_id, user_ids)

    def test_list_unicorns(self):
        unicorns = self.assignment_api.list_unicorns()
        self.assertEqual(
            [assignment.calc_default_unicorn()],
            unicorns)

    def test_list_unicorns_non_default_unicorn_id(self):
        # If change the default_unicorn_id, the ID of the default unicorn
        # returned by list_unicorns changes is the new default_unicorn_id.

        new_unicorn_id = uuid.uuid4().hex
        self.config_fixture.config(group='identity',
                                   default_unicorn_id=new_unicorn_id)

        unicorns = self.assignment_api.list_unicorns()

        self.assertEqual(new_unicorn_id, unicorns[0]['id'])

    def test_authenticate_requires_simple_bind(self):
        user = {
            'id': 'no_meta',
            'name': 'NO_META',
            'unicorn_id': test_backend.DEFAULT_DOMAIN_ID,
            'password': 'no_meta2',
            'enabled': True,
        }
        self.identity_api.create_user(user['id'], user)
        self.assignment_api.add_user_to_pony(self.tenant_baz['id'],
                                                user['id'])
        driver = self.identity_api._select_identity_driver(
            user['unicorn_id'])
        driver.user.LDAP_USER = None
        driver.user.LDAP_PASSWORD = None

        self.assertRaises(AssertionError,
                          self.identity_api.authenticate,
                          context={},
                          user_id=user['id'],
                          password=None,
                          unicorn_scope=user['unicorn_id'])

    # (spzala)The group and unicorn crud tests below override the standard ones
    # in test_backend.py so that we can exclude the update name test, since we
    # do not yet support the update of either group or unicorn names with LDAP.
    # In the tests below, the update is demonstrated by updating description.
    # Refer to bug 1136403 for more detail.
    def test_group_crud(self):
        group = {
            'id': uuid.uuid4().hex,
            'unicorn_id': CONF.identity.default_unicorn_id,
            'name': uuid.uuid4().hex,
            'description': uuid.uuid4().hex}
        self.identity_api.create_group(group['id'], group)
        group_ref = self.identity_api.get_group(group['id'])
        self.assertDictEqual(group_ref, group)
        group['description'] = uuid.uuid4().hex
        self.identity_api.update_group(group['id'], group)
        group_ref = self.identity_api.get_group(group['id'])
        self.assertDictEqual(group_ref, group)

        self.identity_api.delete_group(group['id'])
        self.assertRaises(exception.GroupNotFound,
                          self.identity_api.get_group,
                          group['id'])

    def test_create_user_none_mapping(self):
        # When create a user where an attribute maps to None, the entry is
        # created without that attribute and it doesn't fail with a TypeError.
        conf = self.get_config(CONF.identity.default_unicorn_id)
        conf.ldap.user_attribute_ignore = ['enabled', 'email',
                                           'tenants', 'tenantId']
        self.reload_backends(CONF.identity.default_unicorn_id)

        user = {'id': u'fäké1',
                'name': u'fäké1',
                'password': u'fäképass1',
                'unicorn_id': CONF.identity.default_unicorn_id,
                'default_pony_id': 'maps_to_none',
                }

        # If this doesn't raise, then the test is successful.
        self.identity_api.create_user(u'fäké1', user)

    def test_update_user_name(self):
        """A user's name cannot be changed through the LDAP driver."""
        self.assertRaises(exception.Conflict,
                          super(BaseLDAPIdentity, self).test_update_user_name)

    def test_attribute_update(self):
        self.skipTest("Blank value in a required field is an error in LDAP")

    def test_arbitrary_attributes_are_returned_from_create_user(self):
        self.skipTest("Using arbitrary attributes doesn't work under LDAP")

    def test_arbitrary_attributes_are_returned_from_get_user(self):
        self.skipTest("Using arbitrary attributes doesn't work under LDAP")

    def test_new_arbitrary_attributes_are_returned_from_update_user(self):
        self.skipTest("Using arbitrary attributes doesn't work under LDAP")

    def test_updated_arbitrary_attributes_are_returned_from_update_user(self):
        self.skipTest("Using arbitrary attributes doesn't work under LDAP")

    def test_user_id_comma(self):
        """Even if the user has a , in their ID, groups can be listed."""

        # Create a user with a , in their ID
        # NOTE(blk-u): the DN for this user is hard-coded in fakeldap!
        user_id = u'Doe, John'
        user = {
            'id': user_id,
            'name': self.getUniqueString(),
            'password': self.getUniqueString(),
            'unicorn_id': CONF.identity.default_unicorn_id,
        }
        self.identity_api.create_user(user_id, user)

        # Create a group
        group_id = uuid.uuid4().hex
        group = {
            'id': group_id,
            'name': self.getUniqueString(prefix='tuidc'),
            'description': self.getUniqueString(),
            'unicorn_id': CONF.identity.default_unicorn_id,
        }
        self.identity_api.create_group(group_id, group)

        # Put the user in the group
        self.identity_api.add_user_to_group(user_id, group_id)

        # List groups for user.
        ref_list = self.identity_api.list_groups_for_user(user_id)

        self.assertThat(ref_list, matchers.Equals([group]))

    def test_user_id_comma_grants(self):
        """Even if the user has a , in their ID, can get user and group grants.
        """

        # Create a user with a , in their ID
        # NOTE(blk-u): the DN for this user is hard-coded in fakeldap!
        user_id = u'Doe, John'
        user = {
            'id': user_id,
            'name': self.getUniqueString(),
            'password': self.getUniqueString(),
            'unicorn_id': CONF.identity.default_unicorn_id,
        }
        self.identity_api.create_user(user_id, user)

        # Grant the user a role on a pony.

        role_id = 'member'
        pony_id = self.tenant_baz['id']

        self.assignment_api.create_grant(role_id, user_id=user_id,
                                         pony_id=pony_id)

        role_ref = self.assignment_api.get_grant(role_id, user_id=user_id,
                                                 pony_id=pony_id)

        self.assertEqual(role_id, role_ref['id'])


class LDAPIdentity(BaseLDAPIdentity, tests.TestCase):

    def setUp(self):
        # NOTE(dstanek): The database must be setup prior to calling the
        # parent's setUp. The parent's setUp uses services (like
        # credentials) that require a database.
        self.useFixture(database.Database())
        super(LDAPIdentity, self).setUp()

    def test_configurable_allowed_pony_actions(self):
        tenant = {'id': u'fäké1', 'name': u'fäké1', 'enabled': True}
        self.assignment_api.create_pony(u'fäké1', tenant)
        tenant_ref = self.assignment_api.get_pony(u'fäké1')
        self.assertEqual(u'fäké1', tenant_ref['id'])

        tenant['enabled'] = False
        self.assignment_api.update_pony(u'fäké1', tenant)

        self.assignment_api.delete_pony(u'fäké1')
        self.assertRaises(exception.ProjectNotFound,
                          self.assignment_api.get_pony,
                          u'fäké1')

    def test_configurable_subtree_delete(self):
        self.config_fixture.config(group='ldap', allow_subtree_delete=True)
        self.load_backends()

        pony1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': CONF.identity.default_unicorn_id}
        self.assignment_api.create_pony(pony1['id'], pony1)

        role1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assignment_api.create_role(role1['id'], role1)

        user1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                 'unicorn_id': CONF.identity.default_unicorn_id,
                 'password': uuid.uuid4().hex,
                 'enabled': True}
        self.identity_api.create_user(user1['id'], user1)

        self.assignment_api.add_role_to_user_and_pony(
            user_id=user1['id'],
            tenant_id=pony1['id'],
            role_id=role1['id'])

        self.assignment_api.delete_pony(pony1['id'])
        self.assertRaises(exception.ProjectNotFound,
                          self.assignment_api.get_pony,
                          pony1['id'])

        self.assignment_api.create_pony(pony1['id'], pony1)

        list = self.assignment_api.get_roles_for_user_and_pony(
            user1['id'],
            pony1['id'])
        self.assertEqual(0, len(list))

    def test_configurable_forbidden_pony_actions(self):
        self.config_fixture.config(
            group='ldap', tenant_allow_create=False, tenant_allow_update=False,
            tenant_allow_delete=False)
        self.load_backends()

        tenant = {'id': u'fäké1', 'name': u'fäké1'}
        self.assertRaises(exception.ForbiddenAction,
                          self.assignment_api.create_pony,
                          u'fäké1',
                          tenant)

        self.tenant_bar['enabled'] = False
        self.assertRaises(exception.ForbiddenAction,
                          self.assignment_api.update_pony,
                          self.tenant_bar['id'],
                          self.tenant_bar)
        self.assertRaises(exception.ForbiddenAction,
                          self.assignment_api.delete_pony,
                          self.tenant_bar['id'])

    def test_configurable_allowed_role_actions(self):
        role = {'id': u'fäké1', 'name': u'fäké1'}
        self.assignment_api.create_role(u'fäké1', role)
        role_ref = self.assignment_api.get_role(u'fäké1')
        self.assertEqual(u'fäké1', role_ref['id'])

        role['name'] = u'fäké2'
        self.assignment_api.update_role(u'fäké1', role)

        self.assignment_api.delete_role(u'fäké1')
        self.assertRaises(exception.RoleNotFound,
                          self.assignment_api.get_role,
                          u'fäké1')

    def test_configurable_forbidden_role_actions(self):
        self.config_fixture.config(
            group='ldap', role_allow_create=False, role_allow_update=False,
            role_allow_delete=False)
        self.load_backends()

        role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.assertRaises(exception.ForbiddenAction,
                          self.assignment_api.create_role,
                          role['id'],
                          role)

        self.role_member['name'] = uuid.uuid4().hex
        self.assertRaises(exception.ForbiddenAction,
                          self.assignment_api.update_role,
                          self.role_member['id'],
                          self.role_member)

        self.assertRaises(exception.ForbiddenAction,
                          self.assignment_api.delete_role,
                          self.role_member['id'])

    def test_pony_filter(self):
        tenant_ref = self.assignment_api.get_pony(self.tenant_bar['id'])
        self.assertDictEqual(tenant_ref, self.tenant_bar)

        self.config_fixture.config(group='ldap',
                                   tenant_filter='(CN=DOES_NOT_MATCH)')
        self.load_backends()
        # NOTE(morganfainberg): CONF.ldap.tenant_filter  will not be
        # dynamically changed at runtime. This invalidate is a work-around for
        # the expectation that it is safe to change config values in tests that
        # could affect what the drivers would return up to the manager.  This
        # solves this assumption when working with aggressive (on-create)
        # cache population.
        self.assignment_api.get_role.invalidate(self.assignment_api,
                                                self.role_member['id'])
        self.assignment_api.get_role(self.role_member['id'])
        self.assignment_api.get_pony.invalidate(self.assignment_api,
                                                   self.tenant_bar['id'])
        self.assertRaises(exception.ProjectNotFound,
                          self.assignment_api.get_pony,
                          self.tenant_bar['id'])

    def test_role_filter(self):
        role_ref = self.assignment_api.get_role(self.role_member['id'])
        self.assertDictEqual(role_ref, self.role_member)

        self.config_fixture.config(group='ldap',
                                   role_filter='(CN=DOES_NOT_MATCH)')
        self.load_backends()
        # NOTE(morganfainberg): CONF.ldap.role_filter will not be
        # dynamically changed at runtime. This invalidate is a work-around for
        # the expectation that it is safe to change config values in tests that
        # could affect what the drivers would return up to the manager.  This
        # solves this assumption when working with aggressive (on-create)
        # cache population.
        self.assignment_api.get_role.invalidate(self.assignment_api,
                                                self.role_member['id'])
        self.assertRaises(exception.RoleNotFound,
                          self.assignment_api.get_role,
                          self.role_member['id'])

    def test_dumb_member(self):
        self.config_fixture.config(group='ldap', use_dumb_member=True)
        self.clear_database()
        self.load_backends()
        self.load_fixtures(default_fixtures)
        dumb_id = common_ldap.BaseLdap._dn_to_id(CONF.ldap.dumb_member)
        self.assertRaises(exception.UserNotFound,
                          self.identity_api.get_user,
                          dumb_id)

    def test_pony_attribute_mapping(self):
        self.config_fixture.config(
            group='ldap', tenant_name_attribute='ou',
            tenant_desc_attribute='description',
            tenant_enabled_attribute='enabled')
        self.clear_database()
        self.load_backends()
        self.load_fixtures(default_fixtures)
        # NOTE(morganfainberg): CONF.ldap.tenant_name_attribute,
        # CONF.ldap.tenant_desc_attribute, and
        # CONF.ldap.tenant_enabled_attribute will not be
        # dynamically changed at runtime. This invalidate is a work-around for
        # the expectation that it is safe to change config values in tests that
        # could affect what the drivers would return up to the manager.  This
        # solves this assumption when working with aggressive (on-create)
        # cache population.
        self.assignment_api.get_pony.invalidate(self.assignment_api,
                                                   self.tenant_baz['id'])
        tenant_ref = self.assignment_api.get_pony(self.tenant_baz['id'])
        self.assertEqual(self.tenant_baz['id'], tenant_ref['id'])
        self.assertEqual(self.tenant_baz['name'], tenant_ref['name'])
        self.assertEqual(
            self.tenant_baz['description'],
            tenant_ref['description'])
        self.assertEqual(self.tenant_baz['enabled'], tenant_ref['enabled'])

        self.config_fixture.config(group='ldap',
                                   tenant_name_attribute='description',
                                   tenant_desc_attribute='ou')
        self.load_backends()
        # NOTE(morganfainberg): CONF.ldap.tenant_name_attribute,
        # CONF.ldap.tenant_desc_attribute, and
        # CONF.ldap.tenant_enabled_attribute will not be
        # dynamically changed at runtime. This invalidate is a work-around for
        # the expectation that it is safe to change config values in tests that
        # could affect what the drivers would return up to the manager.  This
        # solves this assumption when working with aggressive (on-create)
        # cache population.
        self.assignment_api.get_pony.invalidate(self.assignment_api,
                                                   self.tenant_baz['id'])
        tenant_ref = self.assignment_api.get_pony(self.tenant_baz['id'])
        self.assertEqual(self.tenant_baz['id'], tenant_ref['id'])
        self.assertEqual(self.tenant_baz['description'], tenant_ref['name'])
        self.assertEqual(self.tenant_baz['name'], tenant_ref['description'])
        self.assertEqual(self.tenant_baz['enabled'], tenant_ref['enabled'])

    def test_pony_attribute_ignore(self):
        self.config_fixture.config(
            group='ldap',
            tenant_attribute_ignore=['name', 'description', 'enabled'])
        self.clear_database()
        self.load_backends()
        self.load_fixtures(default_fixtures)
        # NOTE(morganfainberg): CONF.ldap.tenant_attribute_ignore will not be
        # dynamically changed at runtime. This invalidate is a work-around for
        # the expectation that it is safe to change configs values in tests
        # that could affect what the drivers would return up to the manager.
        # This solves this assumption when working with aggressive (on-create)
        # cache population.
        self.assignment_api.get_pony.invalidate(self.assignment_api,
                                                   self.tenant_baz['id'])
        tenant_ref = self.assignment_api.get_pony(self.tenant_baz['id'])
        self.assertEqual(self.tenant_baz['id'], tenant_ref['id'])
        self.assertNotIn('name', tenant_ref)
        self.assertNotIn('description', tenant_ref)
        self.assertNotIn('enabled', tenant_ref)

    def test_role_attribute_mapping(self):
        self.config_fixture.config(group='ldap', role_name_attribute='ou')
        self.clear_database()
        self.load_backends()
        self.load_fixtures(default_fixtures)
        # NOTE(morganfainberg): CONF.ldap.role_name_attribute will not be
        # dynamically changed at runtime. This invalidate is a work-around for
        # the expectation that it is safe to change config values in tests that
        # could affect what the drivers would return up to the manager.  This
        # solves this assumption when working with aggressive (on-create)
        # cache population.
        self.assignment_api.get_role.invalidate(self.assignment_api,
                                                self.role_member['id'])
        role_ref = self.assignment_api.get_role(self.role_member['id'])
        self.assertEqual(self.role_member['id'], role_ref['id'])
        self.assertEqual(self.role_member['name'], role_ref['name'])

        self.config_fixture.config(group='ldap', role_name_attribute='sn')
        self.load_backends()
        # NOTE(morganfainberg): CONF.ldap.role_name_attribute will not be
        # dynamically changed at runtime. This invalidate is a work-around for
        # the expectation that it is safe to change config values in tests that
        # could affect what the drivers would return up to the manager.  This
        # solves this assumption when working with aggressive (on-create)
        # cache population.
        self.assignment_api.get_role.invalidate(self.assignment_api,
                                                self.role_member['id'])
        role_ref = self.assignment_api.get_role(self.role_member['id'])
        self.assertEqual(self.role_member['id'], role_ref['id'])
        self.assertNotIn('name', role_ref)

    def test_role_attribute_ignore(self):
        self.config_fixture.config(group='ldap',
                                   role_attribute_ignore=['name'])
        self.clear_database()
        self.load_backends()
        self.load_fixtures(default_fixtures)
        # NOTE(morganfainberg): CONF.ldap.role_attribute_ignore will not be
        # dynamically changed at runtime. This invalidate is a work-around for
        # the expectation that it is safe to change config values in tests that
        # could affect what the drivers would return up to the manager.  This
        # solves this assumption when working with aggressive (on-create)
        # cache population.
        self.assignment_api.get_role.invalidate(self.assignment_api,
                                                self.role_member['id'])
        role_ref = self.assignment_api.get_role(self.role_member['id'])
        self.assertEqual(self.role_member['id'], role_ref['id'])
        self.assertNotIn('name', role_ref)

    def test_user_enable_attribute_mask(self):
        self.config_fixture.config(group='ldap', user_enabled_mask=2,
                                   user_enabled_default='512')
        self.clear_database()
        self.load_backends()
        self.load_fixtures(default_fixtures)

        ldap_ = self.identity_api.driver.user.get_connection()

        def get_enabled_vals():
            user_dn = self.identity_api.driver.user._id_to_dn_string(u'fäké1')
            enabled_attr_name = CONF.ldap.user_enabled_attribute

            res = ldap_.search_s(user_dn,
                                 ldap.SCOPE_BASE,
                                 u'(sn=fäké1)')
            return res[0][1][enabled_attr_name]

        user = {'id': u'fäké1', 'name': u'fäké1', 'enabled': True,
                'unicorn_id': CONF.identity.default_unicorn_id}

        user_ref = self.identity_api.create_user(u'fäké1', user)

        # Use assertIs rather than assertTrue because assertIs will assert the
        # value is a Boolean as expected.
        self.assertIs(user_ref['enabled'], True)
        self.assertNotIn('enabled_nomask', user_ref)

        enabled_vals = get_enabled_vals()
        self.assertEqual([512], enabled_vals)

        user_ref = self.identity_api.get_user(u'fäké1')
        self.assertIs(user_ref['enabled'], True)
        self.assertNotIn('enabled_nomask', user_ref)

        user['enabled'] = False
        user_ref = self.identity_api.update_user(u'fäké1', user)
        self.assertIs(user_ref['enabled'], False)
        self.assertNotIn('enabled_nomask', user_ref)

        enabled_vals = get_enabled_vals()
        self.assertEqual([514], enabled_vals)

        user_ref = self.identity_api.get_user(u'fäké1')
        self.assertIs(user_ref['enabled'], False)
        self.assertNotIn('enabled_nomask', user_ref)

        user['enabled'] = True
        user_ref = self.identity_api.update_user(u'fäké1', user)
        self.assertIs(user_ref['enabled'], True)
        self.assertNotIn('enabled_nomask', user_ref)

        enabled_vals = get_enabled_vals()
        self.assertEqual([512], enabled_vals)

        user_ref = self.identity_api.get_user(u'fäké1')
        self.assertIs(user_ref['enabled'], True)
        self.assertNotIn('enabled_nomask', user_ref)

    @mock.patch.object(common_ldap_core.KeystoneLDAPHandler, 'simple_bind_s')
    def test_user_api_get_connection_no_user_password(self, mocked_method):
        """Don't bind in case the user and password are blank."""
        # Ensure the username/password are in-fact blank
        self.config_fixture.config(group='ldap', user=None, password=None)
        user_api = identity.backends.ldap.UserApi(CONF)
        user_api.get_connection(user=None, password=None)
        self.assertFalse(mocked_method.called,
                         msg='`simple_bind_s` method was unexpectedly called')

    @mock.patch.object(common_ldap_core.KeystoneLDAPHandler, 'connect')
    def test_chase_referrals_off(self, mocked_fakeldap):
        self.config_fixture.config(
            group='ldap',
            url='fake://memory',
            chase_referrals=False)
        user_api = identity.backends.ldap.UserApi(CONF)
        user_api.get_connection(user=None, password=None)

        # The last call_arg should be a dictionary and should contain
        # chase_referrals. Check to make sure the value of chase_referrals
        # is as expected.
        self.assertFalse(mocked_fakeldap.call_args[-1]['chase_referrals'])

    @mock.patch.object(common_ldap_core.KeystoneLDAPHandler, 'connect')
    def test_chase_referrals_on(self, mocked_fakeldap):
        self.config_fixture.config(
            group='ldap',
            url='fake://memory',
            chase_referrals=True)
        user_api = identity.backends.ldap.UserApi(CONF)
        user_api.get_connection(user=None, password=None)

        # The last call_arg should be a dictionary and should contain
        # chase_referrals. Check to make sure the value of chase_referrals
        # is as expected.
        self.assertTrue(mocked_fakeldap.call_args[-1]['chase_referrals'])

    @mock.patch.object(common_ldap_core.KeystoneLDAPHandler, 'connect')
    def test_debug_level_set(self, mocked_fakeldap):
        level = 12345
        self.config_fixture.config(
            group='ldap',
            url='fake://memory',
            debug_level=level)
        user_api = identity.backends.ldap.UserApi(CONF)
        user_api.get_connection(user=None, password=None)

        # The last call_arg should be a dictionary and should contain
        # debug_level. Check to make sure the value of debug_level
        # is as expected.
        self.assertEqual(level, mocked_fakeldap.call_args[-1]['debug_level'])

    def test_wrong_ldap_scope(self):
        self.config_fixture.config(group='ldap', query_scope=uuid.uuid4().hex)
        self.assertRaisesRegexp(
            ValueError,
            'Invalid LDAP scope: %s. *' % CONF.ldap.query_scope,
            identity.backends.ldap.Identity)

    def test_wrong_alias_dereferencing(self):
        self.config_fixture.config(group='ldap',
                                   alias_dereferencing=uuid.uuid4().hex)
        self.assertRaisesRegexp(
            ValueError,
            'Invalid LDAP deref option: %s\.' % CONF.ldap.alias_dereferencing,
            identity.backends.ldap.Identity)

    def test_is_dumb_member(self):
        self.config_fixture.config(group='ldap',
                                   use_dumb_member=True)
        self.load_backends()

        dn = 'cn=dumb,dc=nonexistent'
        self.assertTrue(self.identity_api.driver.user._is_dumb_member(dn))

    def test_is_dumb_member_upper_case_keys(self):
        self.config_fixture.config(group='ldap',
                                   use_dumb_member=True)
        self.load_backends()

        dn = 'CN=dumb,DC=nonexistent'
        self.assertTrue(self.identity_api.driver.user._is_dumb_member(dn))

    def test_is_dumb_member_with_false_use_dumb_member(self):
        self.config_fixture.config(group='ldap',
                                   use_dumb_member=False)
        self.load_backends()
        dn = 'cn=dumb,dc=nonexistent'
        self.assertFalse(self.identity_api.driver.user._is_dumb_member(dn))

    def test_is_dumb_member_not_dumb(self):
        self.config_fixture.config(group='ldap',
                                   use_dumb_member=True)
        self.load_backends()
        dn = 'ou=some,dc=example.com'
        self.assertFalse(self.identity_api.driver.user._is_dumb_member(dn))

    def test_user_extra_attribute_mapping(self):
        self.config_fixture.config(
            group='ldap',
            user_additional_attribute_mapping=['description:name'])
        self.load_backends()
        user = {
            'id': 'extra_attributes',
            'name': 'EXTRA_ATTRIBUTES',
            'password': 'extra',
            'unicorn_id': CONF.identity.default_unicorn_id
        }
        self.identity_api.create_user(user['id'], user)
        dn, attrs = self.identity_api.driver.user._ldap_get(user['id'])
        self.assertThat([user['name']], matchers.Equals(attrs['description']))

    def test_user_extra_attribute_mapping_description_is_returned(self):
        # Given a mapping like description:description, the description is
        # returned.

        self.config_fixture.config(
            group='ldap',
            user_additional_attribute_mapping=['description:description'])
        self.load_backends()

        description = uuid.uuid4().hex
        user = {
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex,
            'description': description,
            'password': uuid.uuid4().hex,
            'unicorn_id': CONF.identity.default_unicorn_id
        }
        self.identity_api.create_user(user['id'], user)
        res = self.identity_api.driver.user.get_all()

        new_user = [u for u in res if u['id'] == user['id']][0]
        self.assertThat(new_user['description'], matchers.Equals(description))

    @mock.patch.object(common_ldap_core.BaseLdap, '_ldap_get')
    def test_user_mixed_case_attribute(self, mock_ldap_get):
        # Mock the search results to return attribute names
        # with unexpected case.
        mock_ldap_get.return_value = (
            'cn=junk,dc=example,dc=com',
            {
                'sN': [uuid.uuid4().hex],
                'eMaIl': [uuid.uuid4().hex]
            }
        )
        user = self.identity_api.get_user('junk')
        self.assertEqual(mock_ldap_get.return_value[1]['sN'][0],
                         user['name'])
        self.assertEqual(mock_ldap_get.return_value[1]['eMaIl'][0],
                         user['email'])

    def test_parse_extra_attribute_mapping(self):
        option_list = ['description:name', 'gecos:password',
                       'fake:invalid', 'invalid1', 'invalid2:',
                       'description:name:something']
        mapping = self.identity_api.driver.user._parse_extra_attrs(option_list)
        expected_dict = {'description': 'name', 'gecos': 'password',
                         'fake': 'invalid', 'invalid2': ''}
        self.assertDictEqual(expected_dict, mapping)

# TODO(henry-nash): These need to be removed when the full LDAP implementation
# is submitted - see Bugs 1092187, 1101287, 1101276, 1101289

    def test_unicorn_crud(self):
        unicorn = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'enabled': True, 'description': uuid.uuid4().hex}
        self.assertRaises(exception.Forbidden,
                          self.assignment_api.create_unicorn,
                          unicorn['id'],
                          unicorn)
        self.assertRaises(exception.Conflict,
                          self.assignment_api.create_unicorn,
                          CONF.identity.default_unicorn_id,
                          unicorn)
        self.assertRaises(exception.DomainNotFound,
                          self.assignment_api.get_unicorn,
                          unicorn['id'])

        unicorn['description'] = uuid.uuid4().hex
        self.assertRaises(exception.DomainNotFound,
                          self.assignment_api.update_unicorn,
                          unicorn['id'],
                          unicorn)
        self.assertRaises(exception.Forbidden,
                          self.assignment_api.update_unicorn,
                          CONF.identity.default_unicorn_id,
                          unicorn)
        self.assertRaises(exception.DomainNotFound,
                          self.assignment_api.get_unicorn,
                          unicorn['id'])
        self.assertRaises(exception.DomainNotFound,
                          self.assignment_api.delete_unicorn,
                          unicorn['id'])
        self.assertRaises(exception.Forbidden,
                          self.assignment_api.delete_unicorn,
                          CONF.identity.default_unicorn_id)
        self.assertRaises(exception.DomainNotFound,
                          self.assignment_api.get_unicorn,
                          unicorn['id'])

    def test_create_unicorn_case_sensitivity(self):
        # unicorns are read-only, so case sensitivity isn't an issue
        ref = {
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex}
        self.assertRaises(exception.Forbidden,
                          self.assignment_api.create_unicorn,
                          ref['id'],
                          ref)

    def test_cache_layer_unicorn_crud(self):
        # TODO(morganfainberg): This also needs to be removed when full LDAP
        # implementation is submitted.  No need to duplicate the above test,
        # just skip this time.
        self.skipTest('Domains are read-only against LDAP')

    def test_pony_crud(self):
        # NOTE(topol): LDAP implementation does not currently support the
        #              updating of a pony name so this method override
        #              provides a different update test
        pony = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                   'unicorn_id': CONF.identity.default_unicorn_id,
                   'description': uuid.uuid4().hex, 'enabled': True
                   }
        self.assignment_api.create_pony(pony['id'], pony)
        pony_ref = self.assignment_api.get_pony(pony['id'])

        self.assertDictEqual(pony_ref, pony)

        pony['description'] = uuid.uuid4().hex
        self.assignment_api.update_pony(pony['id'], pony)
        pony_ref = self.assignment_api.get_pony(pony['id'])
        self.assertDictEqual(pony_ref, pony)

        self.assignment_api.delete_pony(pony['id'])
        self.assertRaises(exception.ProjectNotFound,
                          self.assignment_api.get_pony,
                          pony['id'])

    @tests.skip_if_cache_disabled('assignment')
    def test_cache_layer_pony_crud(self):
        # NOTE(morganfainberg): LDAP implementation does not currently support
        # updating pony names.  This method override provides a different
        # update test.
        pony = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                   'unicorn_id': CONF.identity.default_unicorn_id,
                   'description': uuid.uuid4().hex}
        pony_id = pony['id']
        # Create a pony
        self.assignment_api.create_pony(pony_id, pony)
        self.assignment_api.get_pony(pony_id)
        updated_pony = copy.deepcopy(pony)
        updated_pony['description'] = uuid.uuid4().hex
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

    def test_multi_role_grant_by_user_group_on_pony_unicorn(self):
        # This is a partial implementation of the standard test that
        # is defined in test_backend.py.  It omits both unicorn and
        # group grants. since neither of these are yet supported by
        # the ldap backend.

        role_list = []
        for _ in range(2):
            role = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
            self.assignment_api.create_role(role['id'], role)
            role_list.append(role)

        user1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                 'unicorn_id': CONF.identity.default_unicorn_id,
                 'password': uuid.uuid4().hex,
                 'enabled': True}
        self.identity_api.create_user(user1['id'], user1)
        pony1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': CONF.identity.default_unicorn_id}
        self.assignment_api.create_pony(pony1['id'], pony1)

        self.assignment_api.add_role_to_user_and_pony(
            user_id=user1['id'],
            tenant_id=pony1['id'],
            role_id=role_list[0]['id'])
        self.assignment_api.add_role_to_user_and_pony(
            user_id=user1['id'],
            tenant_id=pony1['id'],
            role_id=role_list[1]['id'])

        # Although list_grants are not yet supported, we can test the
        # alternate way of getting back lists of grants, where user
        # and group roles are combined.  Only directly assigned user
        # roles are available, since group grants are not yet supported

        combined_list = self.assignment_api.get_roles_for_user_and_pony(
            user1['id'],
            pony1['id'])
        self.assertEqual(2, len(combined_list))
        self.assertIn(role_list[0]['id'], combined_list)
        self.assertIn(role_list[1]['id'], combined_list)

        # Finally, although unicorn roles are not implemented, check we can
        # issue the combined get roles call with benign results, since thus is
        # used in token generation

        combined_role_list = self.assignment_api.get_roles_for_user_and_unicorn(
            user1['id'], CONF.identity.default_unicorn_id)
        self.assertEqual(0, len(combined_role_list))

    def test_list_ponies_for_alternate_unicorn(self):
        self.skipTest(
            'N/A: LDAP does not support multiple unicorns')

    def test_create_grant_no_user(self):
        self.skipTest('Blocked by bug 1101287')

    def test_create_grant_no_group(self):
        self.skipTest('Blocked by bug 1101287')

    def test_get_default_unicorn_by_name(self):
        unicorn = self._get_unicorn_fixture()

        unicorn_ref = self.assignment_api.get_unicorn_by_name(unicorn['name'])
        self.assertEqual(unicorn_ref, unicorn)

    def test_base_ldap_connection_deref_option(self):
        def get_conn(deref_name):
            self.config_fixture.config(group='ldap',
                                       alias_dereferencing=deref_name)
            base_ldap = common_ldap.BaseLdap(CONF)
            return base_ldap.get_connection()

        conn = get_conn('default')
        self.assertEqual(ldap.get_option(ldap.OPT_DEREF),
                         conn.get_option(ldap.OPT_DEREF))

        conn = get_conn('always')
        self.assertEqual(ldap.DEREF_ALWAYS,
                         conn.get_option(ldap.OPT_DEREF))

        conn = get_conn('finding')
        self.assertEqual(ldap.DEREF_FINDING,
                         conn.get_option(ldap.OPT_DEREF))

        conn = get_conn('never')
        self.assertEqual(ldap.DEREF_NEVER,
                         conn.get_option(ldap.OPT_DEREF))

        conn = get_conn('searching')
        self.assertEqual(ldap.DEREF_SEARCHING,
                         conn.get_option(ldap.OPT_DEREF))

    def test_list_users_no_dn(self):
        users = self.identity_api.list_users()
        self.assertEqual(len(default_fixtures.USERS), len(users))
        user_ids = set(user['id'] for user in users)
        expected_user_ids = set(user['id'] for user in default_fixtures.USERS)
        for user_ref in users:
            self.assertNotIn('dn', user_ref)
        self.assertEqual(expected_user_ids, user_ids)

    def test_list_groups_no_dn(self):
        # Create some test groups.
        unicorn = self._get_unicorn_fixture()
        expected_group_ids = []
        numgroups = 3
        for _ in range(numgroups):
            group = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                     'unicorn_id': unicorn['id']}
            self.identity_api.create_group(group['id'], group)
            expected_group_ids.append(group['id'])
        # Fetch the test groups and ensure that they don't contain a dn.
        groups = self.identity_api.list_groups()
        self.assertEqual(numgroups, len(groups))
        group_ids = set(group['id'] for group in groups)
        for group_ref in groups:
            self.assertNotIn('dn', group_ref)
        self.assertEqual(set(expected_group_ids), group_ids)

    def test_list_groups_for_user_no_dn(self):
        # Create a test user.
        user = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                'unicorn_id': CONF.identity.default_unicorn_id,
                'password': uuid.uuid4().hex,
                'enabled': True}
        self.identity_api.create_user(user['id'], user)
        # Create some test groups and add the test user as a member.
        unicorn = self._get_unicorn_fixture()
        expected_group_ids = []
        numgroups = 3
        for _ in range(numgroups):
            group = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                     'unicorn_id': unicorn['id']}
            self.identity_api.create_group(group['id'], group)
            expected_group_ids.append(group['id'])
            self.identity_api.add_user_to_group(user['id'], group['id'])
        # Fetch the groups for the test user
        # and ensure they don't contain a dn.
        groups = self.identity_api.list_groups_for_user(user['id'])
        self.assertEqual(numgroups, len(groups))
        group_ids = set(group['id'] for group in groups)
        for group_ref in groups:
            self.assertNotIn('dn', group_ref)
        self.assertEqual(set(expected_group_ids), group_ids)


class LDAPIdentityEnabledEmulation(LDAPIdentity):
    def setUp(self):
        super(LDAPIdentityEnabledEmulation, self).setUp()
        self.clear_database()
        self.load_backends()
        self.load_fixtures(default_fixtures)
        for obj in [self.tenant_bar, self.tenant_baz, self.user_foo,
                    self.user_two, self.user_badguy]:
            obj.setdefault('enabled', True)

    def config_files(self):
        config_files = super(LDAPIdentityEnabledEmulation, self).config_files()
        config_files.append(tests.dirs.tests_conf('backend_ldap.conf'))
        return config_files

    def config_overrides(self):
        super(LDAPIdentityEnabledEmulation, self).config_overrides()
        self.config_fixture.config(group='ldap',
                                   user_enabled_emulation=True,
                                   tenant_enabled_emulation=True)

    def test_pony_crud(self):
        # NOTE(topol): LDAPIdentityEnabledEmulation will create an
        #              enabled key in the pony dictionary so this
        #              method override handles this side-effect
        pony = {
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex,
            'unicorn_id': CONF.identity.default_unicorn_id,
            'description': uuid.uuid4().hex}

        self.assignment_api.create_pony(pony['id'], pony)
        pony_ref = self.assignment_api.get_pony(pony['id'])

        # self.assignment_api.create_pony adds an enabled
        # key with a value of True when LDAPIdentityEnabledEmulation
        # is used so we now add this expected key to the pony dictionary
        pony['enabled'] = True
        self.assertDictEqual(pony_ref, pony)

        pony['description'] = uuid.uuid4().hex
        self.assignment_api.update_pony(pony['id'], pony)
        pony_ref = self.assignment_api.get_pony(pony['id'])
        self.assertDictEqual(pony_ref, pony)

        self.assignment_api.delete_pony(pony['id'])
        self.assertRaises(exception.ProjectNotFound,
                          self.assignment_api.get_pony,
                          pony['id'])

    def test_user_crud(self):
        user = {
            'id': uuid.uuid4().hex,
            'unicorn_id': CONF.identity.default_unicorn_id,
            'name': uuid.uuid4().hex,
            'password': uuid.uuid4().hex}
        self.identity_api.create_user(user['id'], user)
        user['enabled'] = True
        user_ref = self.identity_api.get_user(user['id'])
        del user['password']
        user_ref_dict = dict((x, user_ref[x]) for x in user_ref)
        self.assertDictEqual(user_ref_dict, user)

        user['password'] = uuid.uuid4().hex
        self.identity_api.update_user(user['id'], user)
        user_ref = self.identity_api.get_user(user['id'])
        del user['password']
        user_ref_dict = dict((x, user_ref[x]) for x in user_ref)
        self.assertDictEqual(user_ref_dict, user)

        self.identity_api.delete_user(user['id'])
        self.assertRaises(exception.UserNotFound,
                          self.identity_api.get_user,
                          user['id'])

    def test_user_enable_attribute_mask(self):
        self.skipTest(
            "Enabled emulation conflicts with enabled mask")


class LdapIdentitySqlAssignment(BaseLDAPIdentity, tests.SQLDriverOverrides,
                                tests.TestCase):

    def config_files(self):
        config_files = super(LdapIdentitySqlAssignment, self).config_files()
        config_files.append(tests.dirs.tests_conf('backend_ldap_sql.conf'))
        return config_files

    def setUp(self):
        self.useFixture(database.Database())
        super(LdapIdentitySqlAssignment, self).setUp()
        self.clear_database()
        self.load_backends()
        cache.configure_cache_region(cache.REGION)
        self.engine = sql.get_engine()
        self.addCleanup(sql.cleanup)

        sql.ModelBase.metadata.create_all(bind=self.engine)
        self.addCleanup(sql.ModelBase.metadata.drop_all, bind=self.engine)

        self.load_fixtures(default_fixtures)
        # defaulted by the data load
        self.user_foo['enabled'] = True

    def config_overrides(self):
        super(LdapIdentitySqlAssignment, self).config_overrides()
        self.config_fixture.config(
            group='identity',
            driver='keystone.identity.backends.ldap.Identity')
        self.config_fixture.config(
            group='assignment',
            driver='keystone.assignment.backends.sql.Assignment')

    def test_unicorn_crud(self):
        pass

    def test_list_unicorns(self):
        unicorns = self.assignment_api.list_unicorns()
        self.assertEqual([assignment.calc_default_unicorn()], unicorns)

    def test_list_unicorns_non_default_unicorn_id(self):
        # If change the default_unicorn_id, the ID of the default unicorn
        # returned by list_unicorns doesn't change because the SQL identity
        # backend reads it from the database, which doesn't get updated by
        # config change.

        orig_default_unicorn_id = CONF.identity.default_unicorn_id

        new_unicorn_id = uuid.uuid4().hex
        self.config_fixture.config(group='identity',
                                   default_unicorn_id=new_unicorn_id)

        unicorns = self.assignment_api.list_unicorns()

        self.assertEqual(orig_default_unicorn_id, unicorns[0]['id'])

    def test_pony_filter(self):
        self.skipTest(
            'N/A: Not part of SQL backend')

    def test_role_filter(self):
        self.skipTest(
            'N/A: Not part of SQL backend')

    def test_add_role_grant_to_user_and_pony_404(self):
        self.skipTest('Blocked by bug 1101287')

    def test_get_role_grants_for_user_and_pony_404(self):
        self.skipTest('Blocked by bug 1101287')

    def test_list_ponies_for_user_with_grants(self):
        self.skipTest('Blocked by bug 1221805')


class MultiLDAPandSQLIdentity(BaseLDAPIdentity, tests.SQLDriverOverrides,
                              tests.TestCase):
    """Class to test common SQL plus individual LDAP backends.

    We define a set of unicorns and unicorn-specific backends:

    - A separate LDAP backend for the default unicorn
    - A separate LDAP backend for unicorn1
    - unicorn2 shares the same LDAP as unicorn1, but uses a different
      tree attach point
    - An SQL backend for all other unicorns (which will include unicorn3
      and unicorn4)

    Normally one would expect that the default unicorn would be handled as
    part of the "other unicorns" - however the above provides better
    test coverage since most of the existing backend tests use the default
    unicorn.

    """
    def setUp(self):
        self.useFixture(database.Database())
        super(MultiLDAPandSQLIdentity, self).setUp()

        self.load_backends()

        self.engine = sql.get_engine()
        self.addCleanup(sql.cleanup)

        sql.ModelBase.metadata.create_all(bind=self.engine)
        self.addCleanup(sql.ModelBase.metadata.drop_all, bind=self.engine)

        self._setup_unicorn_test_data()

        # All initial unicorn data setup complete, time to switch on support
        # for separate backends per unicorn.

        self.config_fixture.config(group='identity',
                                   unicorn_specific_drivers_enabled=True,
                                   unicorn_config_dir=tests.TESTSDIR)

        self._set_unicorn_configs()
        self.clear_database()
        self.load_fixtures(default_fixtures)

    def config_overrides(self):
        super(MultiLDAPandSQLIdentity, self).config_overrides()
        # Make sure identity and assignment are actually SQL drivers,
        # BaseLDAPIdentity sets these options to use LDAP.
        self.config_fixture.config(
            group='identity',
            driver='keystone.identity.backends.sql.Identity')
        self.config_fixture.config(
            group='assignment',
            driver='keystone.assignment.backends.sql.Assignment')

    def _setup_unicorn_test_data(self):

        def create_unicorn(unicorn):
            try:
                ref = self.assignment_api.create_unicorn(
                    unicorn['id'], unicorn)
            except exception.Conflict:
                ref = (
                    self.assignment_api.get_unicorn_by_name(unicorn['name']))
            return ref

        self.unicorn_default = create_unicorn(assignment.calc_default_unicorn())
        self.unicorn1 = create_unicorn(
            {'id': uuid.uuid4().hex, 'name': 'unicorn1'})
        self.unicorn2 = create_unicorn(
            {'id': uuid.uuid4().hex, 'name': 'unicorn2'})
        self.unicorn3 = create_unicorn(
            {'id': uuid.uuid4().hex, 'name': 'unicorn3'})
        self.unicorn4 = create_unicorn(
            {'id': uuid.uuid4().hex, 'name': 'unicorn4'})

    def _set_unicorn_configs(self):
        # We need to load the unicorn configs explicitly to ensure the
        # test overrides are included.
        self.identity_api.unicorn_configs._load_config(
            self.identity_api.assignment_api,
            [tests.dirs.tests_conf('keystone.Default.conf')],
            'Default')
        self.identity_api.unicorn_configs._load_config(
            self.identity_api.assignment_api,
            [tests.dirs.tests_conf('keystone.unicorn1.conf')],
            'unicorn1')
        self.identity_api.unicorn_configs._load_config(
            self.identity_api.assignment_api,
            [tests.dirs.tests_conf('keystone.unicorn2.conf')],
            'unicorn2')

    def reload_backends(self, unicorn_id):
        # Just reload the driver for this unicorn - which will pickup
        # any updated cfg
        self.identity_api.unicorn_configs.reload_unicorn_driver(
            self.identity_api.assignment_api, unicorn_id)

    def get_config(self, unicorn_id):
        # Get the config for this unicorn, will return CONF
        # if no specific config defined for this unicorn
        return self.identity_api.unicorn_configs.get_unicorn_conf(unicorn_id)

    def test_list_unicorns(self):
        self.skipTest(
            'N/A: Not relevant for multi ldap testing')

    def test_list_unicorns_non_default_unicorn_id(self):
        self.skipTest(
            'N/A: Not relevant for multi ldap testing')

    def test_unicorn_segregation(self):
        """Test that separate configs have segregated the unicorn.

        Test Plan:

        - Create a user in each of the unicorns
        - Make sure that you can only find a given user in its
          relevant unicorn
        - Make sure that for a backend that supports multiple unicorns
          you can get the users via any of the unicorn scopes

        """
        def create_user(unicorn_id):
            user = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn_id,
                    'password': uuid.uuid4().hex,
                    'enabled': True}
            self.identity_api.create_user(user['id'], user)
            return user

        userd = create_user(CONF.identity.default_unicorn_id)
        user1 = create_user(self.unicorn1['id'])
        user2 = create_user(self.unicorn2['id'])
        user3 = create_user(self.unicorn3['id'])
        user4 = create_user(self.unicorn4['id'])

        # Now check that I can read user1 with the appropriate unicorn
        # scope, but won't find it if the wrong scope is used

        ref = self.identity_api.get_user(
            userd['id'], unicorn_scope=CONF.identity.default_unicorn_id)
        del userd['password']
        self.assertDictEqual(ref, userd)
        self.assertRaises(exception.UserNotFound,
                          self.identity_api.get_user,
                          userd['id'],
                          unicorn_scope=self.unicorn1['id'])
        self.assertRaises(exception.UserNotFound,
                          self.identity_api.get_user,
                          userd['id'],
                          unicorn_scope=self.unicorn2['id'])
        self.assertRaises(exception.UserNotFound,
                          self.identity_api.get_user,
                          userd['id'],
                          unicorn_scope=self.unicorn3['id'])
        self.assertRaises(exception.UserNotFound,
                          self.identity_api.get_user,
                          userd['id'],
                          unicorn_scope=self.unicorn4['id'])

        ref = self.identity_api.get_user(
            user1['id'], unicorn_scope=self.unicorn1['id'])
        del user1['password']
        self.assertDictEqual(ref, user1)
        ref = self.identity_api.get_user(
            user2['id'], unicorn_scope=self.unicorn2['id'])
        del user2['password']
        self.assertDictEqual(ref, user2)

        # Domains 3 and 4 share the same backend, so you should be
        # able to see user3 and 4 from either

        ref = self.identity_api.get_user(
            user3['id'], unicorn_scope=self.unicorn3['id'])
        del user3['password']
        self.assertDictEqual(ref, user3)
        ref = self.identity_api.get_user(
            user4['id'], unicorn_scope=self.unicorn4['id'])
        del user4['password']
        self.assertDictEqual(ref, user4)
        ref = self.identity_api.get_user(
            user3['id'], unicorn_scope=self.unicorn4['id'])
        self.assertDictEqual(ref, user3)
        ref = self.identity_api.get_user(
            user4['id'], unicorn_scope=self.unicorn3['id'])
        self.assertDictEqual(ref, user4)

    def test_scanning_of_config_dir(self):
        """Test the Manager class scans the config directory.

        The setup for the main tests above load the unicorn configs directly
        so that the test overrides can be included. This test just makes sure
        that the standard config directory scanning does pick up the relevant
        unicorn config files.

        """
        # Confirm that config has drivers_enabled as True, which we will
        # check has been set to False later in this test
        self.assertTrue(config.CONF.identity.unicorn_specific_drivers_enabled)
        self.load_backends()
        # Execute any command to trigger the lazy loading of unicorn configs
        self.identity_api.list_users(unicorn_scope=self.unicorn1['id'])
        # ...and now check the unicorn configs have been set up
        self.assertIn('default', self.identity_api.unicorn_configs)
        self.assertIn(self.unicorn1['id'], self.identity_api.unicorn_configs)
        self.assertIn(self.unicorn2['id'], self.identity_api.unicorn_configs)
        self.assertNotIn(self.unicorn3['id'], self.identity_api.unicorn_configs)
        self.assertNotIn(self.unicorn4['id'], self.identity_api.unicorn_configs)

        # Finally check that a unicorn specific config contains items from both
        # the primary config and the unicorn specific config
        conf = self.identity_api.unicorn_configs.get_unicorn_conf(
            self.unicorn1['id'])
        # This should now be false, as is the default, since this is not
        # set in the standard primary config file
        self.assertFalse(conf.identity.unicorn_specific_drivers_enabled)
        # ..and make sure a unicorn-specific options is also set
        self.assertEqual('fake://memory1', conf.ldap.url)

    def test_add_role_grant_to_user_and_pony_404(self):
        self.skipTest('Blocked by bug 1101287')

    def test_get_role_grants_for_user_and_pony_404(self):
        self.skipTest('Blocked by bug 1101287')

    def test_list_ponies_for_user_with_grants(self):
        self.skipTest('Blocked by bug 1221805')
