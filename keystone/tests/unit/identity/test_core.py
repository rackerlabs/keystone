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

"""Unit tests for core identity behavior."""

import itertools
import os
import uuid

import mock
from oslo_config import cfg
from oslo_config import fixture as config_fixture

from keystone.common import driver_hints
from keystone import exception
from keystone import identity
from keystone.tests import unit
from keystone.tests.unit.ksfixtures import database


CONF = cfg.CONF


class TestDomainConfigs(unit.BaseTestCase):

    def setUp(self):
        super(TestDomainConfigs, self).setUp()
        self.addCleanup(CONF.reset)

        self.tmp_dir = unit.dirs.tmp()

        self.config_fixture = self.useFixture(config_fixture.Config(CONF))
        self.config_fixture.config(domain_config_dir=self.tmp_dir,
                                   group='identity')

    def test_config_for_nonexistent_domain(self):
        """Having a config for a non-existent domain will be ignored.

        There are no assertions in this test because there are no side
        effects. If there is a config file for a domain that does not
        exist it should be ignored.

        """
        domain_id = uuid.uuid4().hex
        domain_config_filename = os.path.join(self.tmp_dir,
                                              'keystone.%s.conf' % domain_id)
        self.addCleanup(lambda: os.remove(domain_config_filename))
        with open(domain_config_filename, 'w'):
            """Write an empty config file."""

        e = exception.DomainNotFound(domain_id=domain_id)
        mock_assignment_api = mock.Mock()
        mock_assignment_api.get_domain_by_name.side_effect = e

        domain_config = identity.DomainConfigs()
        fake_standard_driver = None
        domain_config.setup_domain_drivers(fake_standard_driver,
                                           mock_assignment_api)

    def test_config_for_dot_name_domain(self):
        # Ensure we can get the right domain name which has dots within it
        # from filename.
        domain_config_filename = os.path.join(self.tmp_dir,
                                              'keystone.abc.def.com.conf')
        with open(domain_config_filename, 'w'):
            """Write an empty config file."""
        self.addCleanup(os.remove, domain_config_filename)

        with mock.patch.object(identity.DomainConfigs,
                               '_load_config_from_file') as mock_load_config:
            domain_config = identity.DomainConfigs()
            fake_assignment_api = None
            fake_standard_driver = None
            domain_config.setup_domain_drivers(fake_standard_driver,
                                               fake_assignment_api)
            mock_load_config.assert_called_once_with(fake_assignment_api,
                                                     [domain_config_filename],
                                                     'abc.def.com')

    def test_config_for_multiple_sql_backend(self):
        domains_config = identity.DomainConfigs()

        # Create the right sequence of is_sql in the drivers being
        # requested to expose the bug, which is that a False setting
        # means it forgets previous True settings.
        drivers = []
        files = []
        for idx, is_sql in enumerate((True, False, True)):
            drv = mock.Mock(is_sql=is_sql)
            drivers.append(drv)
            name = 'dummy.{0}'.format(idx)
            files.append(''.join((
                identity.DOMAIN_CONF_FHEAD,
                name,
                identity.DOMAIN_CONF_FTAIL)))

        walk_fake = lambda *a, **kwa: (
            ('/fake/keystone/domains/config', [], files), )

        generic_driver = mock.Mock(is_sql=False)

        assignment_api = mock.Mock()
        id_factory = itertools.count()
        assignment_api.get_domain_by_name.side_effect = (
            lambda name: {'id': next(id_factory), '_': 'fake_domain'})
        load_driver_mock = mock.Mock(side_effect=drivers)

        with mock.patch.object(os, 'walk', walk_fake):
            with mock.patch.object(identity.cfg, 'ConfigOpts'):
                with mock.patch.object(domains_config, '_load_driver',
                                       load_driver_mock):
                    self.assertRaises(
                        exception.MultipleSQLDriversInConfig,
                        domains_config.setup_domain_drivers,
                        generic_driver, assignment_api)

                    self.assertEqual(3, load_driver_mock.call_count)


class TestDatabaseDomainConfigs(unit.TestCase):

    def setUp(self):
        super(TestDatabaseDomainConfigs, self).setUp()
        self.useFixture(database.Database())
        self.load_backends()

    def test_domain_config_in_database_disabled_by_default(self):
        self.assertFalse(CONF.identity.domain_configurations_from_database)

    def test_loading_config_from_database(self):
        self.config_fixture.config(domain_configurations_from_database=True,
                                   group='identity')
        domain = unit.new_domain_ref()
        self.resource_api.create_domain(domain['id'], domain)
        # Override two config options for our domain
        conf = {'ldap': {'url': uuid.uuid4().hex,
                         'suffix': uuid.uuid4().hex,
                         'use_tls': 'True'},
                'identity': {
                    'driver': 'ldap'}}
        self.domain_config_api.create_config(domain['id'], conf)
        fake_standard_driver = None
        domain_config = identity.DomainConfigs()
        domain_config.setup_domain_drivers(fake_standard_driver,
                                           self.resource_api)
        # Make sure our two overrides are in place, and others are not affected
        res = domain_config.get_domain_conf(domain['id'])
        self.assertEqual(conf['ldap']['url'], res.ldap.url)
        self.assertEqual(conf['ldap']['suffix'], res.ldap.suffix)
        self.assertEqual(CONF.ldap.query_scope, res.ldap.query_scope)

        # Make sure the override is not changing the type of the config value
        use_tls_type = type(CONF.ldap.use_tls)
        self.assertEqual(use_tls_type(conf['ldap']['use_tls']),
                         res.ldap.use_tls)

        # Now turn off using database domain configuration and check that the
        # default config file values are now seen instead of the overrides.
        CONF.set_override('domain_configurations_from_database', False,
                          'identity', enforce_type=True)
        domain_config = identity.DomainConfigs()
        domain_config.setup_domain_drivers(fake_standard_driver,
                                           self.resource_api)
        res = domain_config.get_domain_conf(domain['id'])
        self.assertEqual(CONF.ldap.url, res.ldap.url)
        self.assertEqual(CONF.ldap.suffix, res.ldap.suffix)
        self.assertEqual(CONF.ldap.use_tls, res.ldap.use_tls)
        self.assertEqual(CONF.ldap.query_scope, res.ldap.query_scope)


class IdentityDriverV8Tests(object):
    driver = None  # subclasses must override driver to the actual driver.

    # subclasses that don't allow name updates must set this to False.
    allows_name_update = True

    # Subclasses must override this to indicate whether it's domain-aware or
    # not.
    expected_is_domain_aware = True

    # Subclasses must override this to the expected default assignment driver.
    expected_default_assignment_driver = 'sql'

    # Subclasses must override this to the expected is_sql value.
    expected_is_sql = False

    # Subclasses must override this to the expected expected_generates_uuids
    # value.
    expected_generates_uuids = True

    def create_user(self, domain_id=None, **kwargs):
        user_id = uuid.uuid4().hex
        user = {
            'id': user_id,
            'name': uuid.uuid4().hex,
            'enabled': True,
        }
        if self.driver.is_domain_aware():
            user['domain_id'] = domain_id or uuid.uuid4().hex
        user.update(kwargs)
        return self.driver.create_user(user_id, user)

    def create_group(self, domain_id=None):
        group_id = uuid.uuid4().hex
        group = {
            'id': group_id,
            'name': uuid.uuid4().hex,
        }
        if self.driver.is_domain_aware():
            group['domain_id'] = domain_id or uuid.uuid4().hex
        return self.driver.create_group(group_id, group)

    def test_is_domain_aware(self):
        self.assertIs(self.expected_is_domain_aware,
                      self.driver.is_domain_aware())

    def test_default_assignment_driver(self):
        self.assertEqual(self.expected_default_assignment_driver,
                         self.driver.default_assignment_driver())

    def test_is_sql(self):
        self.assertIs(self.expected_is_sql, self.driver.is_sql)

    def test_generates_uuids(self):
        self.assertIs(self.expected_generates_uuids,
                      self.driver.generates_uuids())

    def test_create_user(self):
        user_id = uuid.uuid4().hex
        user = {
            'id': user_id,
            'name': uuid.uuid4().hex,
            'enabled': True
        }
        if self.driver.is_domain_aware():
            user['domain_id'] = uuid.uuid4().hex
        ret = self.driver.create_user(user_id, user)
        self.assertEqual(user_id, ret['id'])

    def test_create_user_all_attributes(self):
        user_id = uuid.uuid4().hex
        user = {
            'id': user_id,
            'name': uuid.uuid4().hex,
            'password': uuid.uuid4().hex,
            'enabled': True,
            'default_project_id': uuid.uuid4().hex,
        }
        if self.driver.is_domain_aware():
            user['domain_id'] = uuid.uuid4().hex
        ret = self.driver.create_user(user_id, user)
        exp_user = user.copy()
        del exp_user['password']
        self.assertEqual(exp_user, ret)

    def test_create_user_same_id_exc(self):
        user_id = uuid.uuid4().hex
        user = {
            'id': user_id,
            'name': uuid.uuid4().hex,
            'enabled': True,
        }
        if self.driver.is_domain_aware():
            user['domain_id'] = uuid.uuid4().hex
        self.driver.create_user(user_id, user)
        self.assertRaises(exception.Conflict,
                          self.driver.create_user, user_id, user)

    def test_create_user_same_name_and_domain_exc(self):
        user1_id = uuid.uuid4().hex
        name = uuid.uuid4().hex
        domain_id = uuid.uuid4().hex
        user = {
            'id': user1_id,
            'name': name,
            'enabled': True,
        }
        if self.driver.is_domain_aware():
            user['domain_id'] = domain_id
        self.driver.create_user(user1_id, user)

        user2_id = uuid.uuid4().hex
        user = {
            'id': user2_id,
            'name': name,
            'enabled': True,
        }
        if self.driver.is_domain_aware():
            user['domain_id'] = domain_id
        self.assertRaises(exception.Conflict,
                          self.driver.create_user, user2_id, user)

    def test_list_users_no_users(self):
        hints = driver_hints.Hints()
        self.assertEqual([], self.driver.list_users(hints))

    def test_list_users_when_users(self):
        user = self.create_user()

        hints = driver_hints.Hints()
        users = self.driver.list_users(hints)
        self.assertEqual([user['id']], [u['id'] for u in users])

    def test_get_user(self):
        user = self.create_user()

        actual_user = self.driver.get_user(user['id'])
        self.assertEqual(user['id'], actual_user['id'])

    def test_get_user_no_user_exc(self):
        self.assertRaises(exception.UserNotFound,
                          self.driver.get_user, uuid.uuid4().hex)

    def test_get_user_by_name(self):
        domain_id = uuid.uuid4().hex
        user = self.create_user(domain_id=domain_id)

        actual_user = self.driver.get_user_by_name(user['name'], domain_id)
        self.assertEqual(user['id'], actual_user['id'])

    def test_get_user_by_name_no_user_exc(self):
        # When the user doesn't exist, UserNotFound is raised.
        self.assertRaises(
            exception.UserNotFound, self.driver.get_user_by_name,
            user_name=uuid.uuid4().hex, domain_id=uuid.uuid4().hex)

    def test_update_user(self):
        user = self.create_user()

        user_mod = {'enabled': False}
        actual_user = self.driver.update_user(user['id'], user_mod)
        self.assertEqual(user['id'], actual_user['id'])
        self.assertIs(False, actual_user['enabled'])

    def test_update_user_remove_optional_attribute(self):
        # When the attribute has a value of None it's supposed to be removed.
        user = self.create_user(default_project_id=uuid.uuid4().hex)
        self.assertIn('default_project_id', user)

        user_mod = {'default_project_id': None}
        actual_user = self.driver.update_user(user['id'], user_mod)
        self.assertNotIn('default_project_id', actual_user)

    def test_update_user_same_name_exc(self):
        # For drivers that allow name update, if the name of a user is changed
        # to the same as another user in the same domain, Conflict is raised.

        if not self.allows_name_update:
            self.skipTest("Backend doesn't allow name update.")

        domain_id = uuid.uuid4().hex
        user1 = self.create_user(domain_id=domain_id)
        user2 = self.create_user(domain_id=domain_id)

        user_mod = {'name': user2['name']}
        self.assertRaises(exception.Conflict, self.driver.update_user,
                          user1['id'], user_mod)

    def test_update_user_no_user_exc(self):
        user_id = uuid.uuid4().hex
        user_mod = {'enabled': False}
        self.assertRaises(exception.UserNotFound,
                          self.driver.update_user, user_id, user_mod)

    def test_update_user_name_not_allowed_exc(self):
        # For drivers that do not allow name update, attempting to change the
        # name causes an exception.

        if self.allows_name_update:
            self.skipTest("Backend allows name update.")

        user = self.create_user()
        user_mod = {'name': uuid.uuid4().hex}
        self.assertRaises(exception.Conflict, self.driver.update_user,
                          user['id'], user_mod)

    def test_delete_user(self):
        user = self.create_user()

        self.driver.delete_user(user['id'])
        self.assertRaises(exception.UserNotFound, self.driver.get_user,
                          user['id'])

    def test_delete_user_no_user_exc(self):
        # When the user doesn't exist, UserNotFound is raised.
        self.assertRaises(exception.UserNotFound, self.driver.delete_user,
                          user_id=uuid.uuid4().hex)

    def test_create_group(self):
        group_id = uuid.uuid4().hex
        group = {
            'id': group_id,
            'name': uuid.uuid4().hex,
        }
        if self.driver.is_domain_aware():
            group['domain_id'] = uuid.uuid4().hex
        new_group = self.driver.create_group(group_id, group)
        self.assertEqual(group_id, new_group['id'])

    def test_create_group_all_attrs(self):
        group_id = uuid.uuid4().hex
        group = {
            'id': group_id,
            'name': uuid.uuid4().hex,
            'description': uuid.uuid4().hex,
        }
        if self.driver.is_domain_aware():
            group['domain_id'] = uuid.uuid4().hex
        new_group = self.driver.create_group(group_id, group)
        self.assertEqual(group, new_group)

    def test_create_group_duplicate_exc(self):
        group1_id = uuid.uuid4().hex
        name = uuid.uuid4().hex
        domain = uuid.uuid4().hex
        group1 = {
            'id': group1_id,
            'name': name,
        }
        if self.driver.is_domain_aware():
            group1['domain_id'] = domain
        self.driver.create_group(group1_id, group1)

        group2_id = uuid.uuid4().hex
        group2 = {
            'id': group2_id,
            'name': name,
        }
        if self.driver.is_domain_aware():
            group2['domain_id'] = domain
        self.assertRaises(exception.Conflict, self.driver.create_group,
                          group2_id, group2)

    def test_get_group(self):
        group = self.create_group()

        actual_group = self.driver.get_group(group['id'])
        self.assertEqual(group['id'], actual_group['id'])

    def test_get_group_no_group_exc(self):
        # When the group doesn't exist, get_group raises GroupNotFound.
        self.assertRaises(exception.GroupNotFound, self.driver.get_group,
                          group_id=uuid.uuid4().hex)

    def test_get_group_by_name(self):
        domain_id = uuid.uuid4().hex
        group = self.create_group(domain_id=domain_id)

        actual_group = self.driver.get_group_by_name(group['name'], domain_id)
        self.assertEqual(group['id'], actual_group['id'])

    def test_get_group_by_name_no_user_exc(self):
        # When the group doesn't exist, get_group raises GroupNotFound.
        self.assertRaises(
            exception.GroupNotFound, self.driver.get_group_by_name,
            group_name=uuid.uuid4().hex, domain_id=uuid.uuid4().hex)

    def test_update_group(self):
        group = self.create_group()

        new_description = uuid.uuid4().hex
        group_mod = {'description': new_description}
        actual_group = self.driver.update_group(group['id'], group_mod)
        self.assertEqual(new_description, actual_group['description'])

    def test_update_group_no_group(self):
        # When the group doesn't exist, GroupNotFound is raised.
        group_mod = {'description': uuid.uuid4().hex}
        self.assertRaises(exception.GroupNotFound, self.driver.update_group,
                          group_id=uuid.uuid4().hex, group=group_mod)

    def test_update_group_name_already_exists(self):
        # For drivers that support renaming, when the group is renamed to a
        # name that already exists, Conflict is raised.

        if not self.allows_name_update:
            self.skipTest("driver doesn't allow name update")

        domain_id = uuid.uuid4().hex
        group1 = self.create_group(domain_id=domain_id)
        group2 = self.create_group(domain_id=domain_id)

        group_mod = {'name': group1['name']}
        self.assertRaises(exception.Conflict, self.driver.update_group,
                          group2['id'], group_mod)

    def test_update_group_name_not_allowed(self):
        # For drivers that do not support renaming, when the group is attempted
        # to be renamed ValidationError is raised.

        if self.allows_name_update:
            self.skipTest("driver allows name update")

        group = self.create_group()

        group_mod = {'name': uuid.uuid4().hex}
        self.assertRaises(exception.ValidationError, self.driver.update_group,
                          group['id'], group_mod)

    def test_delete_group(self):
        group = self.create_group()
        self.driver.delete_group(group['id'])
        self.assertRaises(exception.GroupNotFound, self.driver.get_group,
                          group['id'])

    def test_delete_group_doesnt_exist_exc(self):
        self.assertRaises(exception.GroupNotFound, self.driver.delete_group,
                          group_id=uuid.uuid4().hex)

    def test_list_groups_no_groups(self):
        groups = self.driver.list_groups(driver_hints.Hints())
        self.assertEqual([], groups)

    def test_list_groups_one_group(self):
        group = self.create_group()
        groups = self.driver.list_groups(driver_hints.Hints())
        self.assertEqual(group['id'], groups[0]['id'])

    def test_add_user_to_group(self):
        user = self.create_user()
        group = self.create_group()

        self.driver.add_user_to_group(user['id'], group['id'])

        # No assert since if doesn't raise, then successful.
        self.driver.check_user_in_group(user['id'], group['id'])

    def test_add_user_to_group_no_user_exc(self):
        group = self.create_group()

        user_id = uuid.uuid4().hex
        self.assertRaises(exception.UserNotFound,
                          self.driver.add_user_to_group, user_id, group['id'])

    def test_add_user_to_group_no_group_exc(self):
        user = self.create_user()

        group_id = uuid.uuid4().hex
        self.assertRaises(exception.GroupNotFound,
                          self.driver.add_user_to_group, user['id'], group_id)

    def test_check_user_in_group(self):
        user = self.create_user()
        group = self.create_group()
        self.driver.add_user_to_group(user['id'], group['id'])

        # No assert since if doesn't raise, then successful.
        self.driver.check_user_in_group(user['id'], group['id'])

    def test_check_user_in_group_user_not_in_group_exc(self):
        user = self.create_user()
        group = self.create_group()

        self.assertRaises(exception.NotFound, self.driver.check_user_in_group,
                          user['id'], group['id'])

    def test_check_user_in_group_user_doesnt_exist_exc(self):
        # When the user doesn't exist, UserNotFound is raised.
        group = self.create_group()

        user_id = uuid.uuid4().hex
        self.assertRaises(
            exception.UserNotFound, self.driver.check_user_in_group, user_id,
            group['id'])

    def test_check_user_in_group_group_doesnt_exist_exc(self):
        # When the group doesn't exist, UserNotFound is raised.
        user = self.create_user()

        group_id = uuid.uuid4().hex
        self.assertRaises(
            exception.GroupNotFound, self.driver.check_user_in_group,
            user['id'], group_id)

    def test_list_users_in_group_no_users(self):
        group = self.create_group()

        users = self.driver.list_users_in_group(group['id'],
                                                driver_hints.Hints())
        self.assertEqual([], users)

    def test_list_users_in_group_user(self):
        group = self.create_group()
        user = self.create_user()
        self.driver.add_user_to_group(user['id'], group['id'])

        users = self.driver.list_users_in_group(group['id'],
                                                driver_hints.Hints())
        self.assertEqual([user['id']], [u['id'] for u in users])

    def test_list_users_in_group_no_group(self):
        group_id = uuid.uuid4().hex
        self.assertRaises(
            exception.GroupNotFound, self.driver.list_users_in_group, group_id,
            driver_hints.Hints())

    def test_list_groups_for_user_no_groups(self):
        user = self.create_user()

        groups = self.driver.list_groups_for_user(user['id'],
                                                  driver_hints.Hints())
        self.assertEqual([], groups)

    def test_list_groups_for_user_group(self):
        user = self.create_user()
        group = self.create_group()
        self.driver.add_user_to_group(user['id'], group['id'])

        groups = self.driver.list_groups_for_user(user['id'],
                                                  driver_hints.Hints())
        self.assertEqual([group['id']], [g['id'] for g in groups])

    def test_list_groups_for_user_no_user(self):
        user_id = uuid.uuid4().hex
        self.assertRaises(
            exception.UserNotFound, self.driver.list_groups_for_user,
            user_id, driver_hints.Hints())

    def test_remove_user_from_group(self):
        user = self.create_user()
        group = self.create_group()
        self.driver.add_user_to_group(user['id'], group['id'])

        self.driver.remove_user_from_group(user['id'], group['id'])

        self.assertRaises(exception.NotFound, self.driver.check_user_in_group,
                          user['id'], group['id'])

    def test_remove_user_from_group_not_in_group(self):
        user = self.create_user()
        group = self.create_group()

        # FIXME(blk-u): ldap is returning UserNotFound rather than NotFound,
        # fix this.
        self.assertRaises(
            exception.NotFound, self.driver.remove_user_from_group, user['id'],
            group['id'])

    def test_remove_user_from_group_no_user(self):
        group = self.create_group()

        user_id = uuid.uuid4().hex
        self.assertRaises(
            exception.UserNotFound, self.driver.remove_user_from_group,
            user_id, group['id'])

    def test_remove_user_from_group_no_group(self):
        user = self.create_user()

        group_id = uuid.uuid4().hex
        self.assertRaises(
            exception.GroupNotFound, self.driver.remove_user_from_group,
            user['id'], group_id)

    def test_authenticate(self):
        password = uuid.uuid4().hex
        user = self.create_user(password=password)

        actual_user = self.driver.authenticate(user['id'], password)
        self.assertEqual(user['id'], actual_user['id'])

    def test_authenticate_wrong_password(self):
        user = self.create_user(password=uuid.uuid4().hex)

        password = uuid.uuid4().hex
        self.assertRaises(AssertionError, self.driver.authenticate, user['id'],
                          password)

    def test_authenticate_no_user(self):
        user_id = uuid.uuid4().hex
        password = uuid.uuid4().hex
        self.assertRaises(AssertionError, self.driver.authenticate, user_id,
                          password)
