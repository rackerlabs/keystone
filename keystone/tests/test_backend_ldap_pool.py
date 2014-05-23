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

import ldappool
import mock

from keystone.common.ldap import core as ldap_core
from keystone import config
from keystone import tests
from keystone.tests import fakeldap
from keystone.tests import test_backend_ldap

CONF = config.CONF


class LdapPoolCommonTestMixin(object):
    """Ldap pool specific common tests used here and in live tests."""

    def test_handler_with_use_pool_enabled(self):
        user_ref = self.identity_api.get_user(self.user_foo['id'])
        self.user_foo.pop('password')
        self.assertDictEqual(user_ref, self.user_foo)

        handler = ldap_core._get_connection(CONF.ldap.url, use_pool=True)
        self.assertIsInstance(handler, ldap_core.PooledLDAPHandler)

    def test_handler_with_use_pool_not_enabled(self):
        user_ref = self.identity_api.get_user(self.user_foo['id'])
        self.user_foo.pop('password')
        self.assertDictEqual(user_ref, self.user_foo)

        handler = ldap_core._get_connection(CONF.ldap.url, use_pool=False)
        self.assertIsInstance(handler, ldap_core.LDAPHandler)

    def test_pool_size_set(self):
        # get related connection manager instance
        ldappool_cm = ldap_core.CONNECTION_POOLS[CONF.ldap.url]
        self.assertEqual(CONF.ldap.pool_size, ldappool_cm.size)

    def test_pool_retry_max_set(self):
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
        # get related connection manager instance
        ldappool_cm = ldap_core.CONNECTION_POOLS[CONF.ldap.url]
        self.assertEqual(CONF.ldap.use_tls, ldappool_cm.use_tls)

    def test_pool_timeout_set(self):
        # get related connection manager instance
        ldappool_cm = ldap_core.CONNECTION_POOLS[CONF.ldap.url]
        self.assertEqual(CONF.ldap.pool_connection_timeout,
                         ldappool_cm.timeout)

    def test_pool_use_pool_set(self):
        # get related connection manager instance
        ldappool_cm = ldap_core.CONNECTION_POOLS[CONF.ldap.url]
        self.assertEqual(CONF.ldap.use_pool, ldappool_cm.use_pool)

    def test_pool_connection_lifetime_set(self):
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


class LdapIdentitySqlAssignment(test_backend_ldap.LdapIdentitySqlAssignment,
                                tests.TestCase, LdapPoolCommonTestMixin):
    '''Executes existing base class 150+ tests with pooled ldap handler to make
    sure it works without any error.
    '''
    def setUp(self):
        patcher = mock.patch.object(ldap_core.PooledLDAPHandler, 'Connector',
                                    fakeldap.FakeLdapPool)
        patcher.start()
        self.addCleanup(patcher.stop)
        super(LdapIdentitySqlAssignment, self).setUp()
        # super class loads db fixtures which establishes ldap connection
        # so adding dummy call to highlight connection pool initialization
        # as its not that obvious though its not needed here
        self.identity_api.get_user(self.user_foo['id'])

    def config_files(self):
        config_files = super(LdapIdentitySqlAssignment, self).config_files()
        config_files.append(tests.dirs.tests_conf('backend_ldap_pool.conf'))
        return config_files

    def tearDown(self):
        # remove pool changes in a test if any
        ldap_core.CONNECTION_POOLS.pop(CONF.ldap.url, None)
        super(LdapIdentitySqlAssignment, self).tearDown()
