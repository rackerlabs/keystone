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


import ldappool


from keystone.common.ldap import core as ldap_core
from keystone import config
from keystone import tests
from keystone.tests import fakeldap
from keystone.tests import test_ldap_livetest


CONF = config.CONF


class LiveLDAPPoolIdentity(test_ldap_livetest.LiveLDAPIdentity):

    def setUp(self):
        self._ldap_skip_live()
        super(LiveLDAPPoolIdentity, self).setUp()

    def _ldap_skip_live(self):
            self.skip_if_env_not_set('ENABLE_LDAP_LIVE_TEST')

    def config_files(self):
        config_files = super(LiveLDAPPoolIdentity, self).config_files()
        config_files.append(tests.dirs.
                            tests_conf('backend_pool_liveldap.conf'))
        return config_files

    def config_overrides(self):
        super(LiveLDAPPoolIdentity, self).config_overrides()
        self.config_fixture.config(
            group='identity',
            driver='keystone.identity.backends.ldap.Identity')

    def tearDown(self):
        # remove pool changes in a test if any
        ldap_core.CONNECTION_POOLS.pop(CONF.ldap.url, None)
        tests.TestCase.tearDown(self)

    def test_pool_handler_is_instantiated(self):
        self.identity_api.get_user(self.user_foo['id'])

        handler = ldap_core._get_connection(CONF.ldap.url)
        self.assertIsInstance(handler, ldap_core.PooledLDAPHandler)

    def test_assert_connector_cls_not_fake_ldap_pool(self):
        handler = ldap_core._get_connection(CONF.ldap.url)
        self.assertNotEqual(type(handler.CONNECTOR_CLS),
                            type(fakeldap.FakeLdapPool))
        self.assertEqual(type(handler.CONNECTOR_CLS),
                         type(ldappool.StateConnector))

    def test_pool_size_set(self):
        # just make one identity call to initiate ldap connection if not there
        self.identity_api.get_user(self.user_foo['id'])

        # get related connection manager instance
        ldappool_cm = ldap_core.CONNECTION_POOLS[CONF.ldap.url]
        self.assertEqual(CONF.ldap.pool_size, ldappool_cm.size)

    def test_pool_retry_max_set(self):
        # just make one identity call to initiate ldap connection if not there
        self.identity_api.get_user(self.user_foo['id'])

        # get related connection manager instance
        ldappool_cm = ldap_core.CONNECTION_POOLS[CONF.ldap.url]
        self.assertEqual(CONF.ldap.pool_retry_max, ldappool_cm.retry_max)

    def test_pool_retry_delay_set(self):
        # just make one identity call to initiate ldap connection if not there
        self.identity_api.get_user(self.user_foo['id'])

        # get related connection manager instance
        ldappool_cm = ldap_core.CONNECTION_POOLS[CONF.ldap.url]
        self.assertEqual(CONF.ldap.pool_retry_delay, ldappool_cm.retry_delay)

    def test_pool_use_tls_set(self):
        # just make one identity call to initiate ldap connection if not there
        self.identity_api.get_user(self.user_foo['id'])

        # get related connection manager instance
        ldappool_cm = ldap_core.CONNECTION_POOLS[CONF.ldap.url]
        self.assertEqual(CONF.ldap.use_tls, ldappool_cm.use_tls)

    def test_pool_timeout_set(self):
        # just make one identity call to initiate ldap connection if not there
        self.identity_api.get_user(self.user_foo['id'])

        # get related connection manager instance
        ldappool_cm = ldap_core.CONNECTION_POOLS[CONF.ldap.url]
        self.assertEqual(CONF.ldap.pool_connection_timeout,
                         ldappool_cm.timeout)

    def test_pool_use_pool_set(self):
        # just make one identity call to initiate ldap connection if not there
        self.identity_api.get_user(self.user_foo['id'])

        # get related connection manager instance
        ldappool_cm = ldap_core.CONNECTION_POOLS[CONF.ldap.url]
        self.assertEqual(CONF.ldap.use_pool, ldappool_cm.use_pool)

    def test_pool_connection_lifetime_set(self):
        # just make one identity call to initiate ldap connection if not there
        self.identity_api.get_user(self.user_foo['id'])

        # get related connection manager instance
        ldappool_cm = ldap_core.CONNECTION_POOLS[CONF.ldap.url]
        self.assertEqual(CONF.ldap.pool_connection_lifetime,
                         ldappool_cm.max_lifetime)

    def test_max_connection_error_raised(self):

        who = CONF.ldap.user
        cred = CONF.ldap.password
        # get related connection manager instance
        ldappool_cm = ldap_core.CONNECTION_POOLS[CONF.ldap.url]
        ldappool_cm.size = 2

        # 3rd connection attempt should raise Max connection error
        with ldappool_cm.connection(who, cred) as _:  # conn1
            with ldappool_cm.connection(who, cred) as _:  # conn2
                try:
                    with ldappool_cm.connection(who, cred) as _:  # conn3
                        _.unbind_s()
                        self.fail()
                except Exception as ex:
                    self.assertIsInstance(ex,
                                          ldappool.MaxConnectionReachedError)
        ldappool_cm.size = CONF.ldap.pool_size

        # remove pool changes
        del ldap_core.CONNECTION_POOLS[CONF.ldap.url]
