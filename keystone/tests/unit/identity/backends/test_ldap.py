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

import os
import uuid

import ldap3
from oslo_config import fixture as config_fixture

from keystone.identity.backends import ldap
from keystone.tests.unit import core
from keystone.tests.unit.identity.backends import test_base
from keystone.tests.unit.ksfixtures import ldapdb


class TestIdentityDriver(core.BaseTestCase,
                         test_base.IdentityDriverV8Tests):

    allows_name_update = False
    expected_is_domain_aware = False
    expected_default_assignment_driver = 'sql'
    expected_is_sql = False
    expected_generates_uuids = False

    def configure_ldap_server(self):
        config_fixture_ = self.useFixture(config_fixture.Config())
        config_fixture_.config(
            group='ldap',
            url='fake://memory',
            user='cn=Admin',
            password='password',
            suffix='cn=example,cn=com')
        self.useFixture(ldapdb.LDAPDatabase())

    def setUp(self):
        super(TestIdentityDriver, self).setUp()
        self.configure_ldap_server()
        self.driver = ldap.Identity()


ldap_available = None


class OpportunisticLiveIdentityDriverTest(TestIdentityDriver):
    """Opportunistic tests for the Identity driver.

    These tests will run if there's an LDAP server available to run against.
    The following environment variables configure connection and test
    parameters:

    * OS_TEST_LDAP_SERVER_HOSTNAME - host for the LDAP server. Defaults to
      ``localhost``.
    * OS_TEST_LDAP_USER_DN - User to bind as. Defaults to
      ``cn=Manager,dc=openstack,dc=org``.
    * OS_TEST_LDAP_USER_PASSWORD - User password. Defaults to ``password``.
    * OS_TEST_LDAP_BASE_DN - DN of entry to create test entries under. This
      entry must exist already. Defaults to
      ``ou=keystone-test,dc=openstack,dc=org``.

    """

    server_name = os.getenv('OS_TEST_LDAP_SERVER_HOSTNAME', 'localhost')
    user_dn = os.getenv('OS_TEST_LDAP_USER_DN',
                        'cn=Manager,dc=openstack,dc=org')
    password = os.getenv('OS_TEST_LDAP_USER_PASSWORD', 'password')
    base_dn = os.getenv('OS_TEST_LDAP_BASE_DN',
                        'ou=keystone-test,dc=openstack,dc=org')

    def delete_test_entry(self):
        with ldap3.Connection(self.server_name, user=self.user_dn,
                              password=self.password) as conn:
            conn.search(self.test_dn, '(objectclass=*)', attributes=['1.1'])
            dns = sorted((e.entry_get_dn() for e in conn.entries), key=len)
            for dn in dns:
                conn.delete(dn)

    def configure_ldap_server(self):
        global ldap_available

        if ldap_available is False:
            self.skipTest('LDAP server is not available.')

        self.test_dn = 'ou=%s,%s' % (uuid.uuid4().hex, self.base_dn)
        enabled_emulation_dn = 'cn=UsersEnabled,%s' % self.test_dn

        try:
            with ldap3.Connection(self.server_name, user=self.user_dn,
                                  password=self.password) as conn:
                conn.add(self.test_dn, 'organizationalUnit')

                # NOTE(blk-u): conn.add doesn't raise when it failed?
                res = conn.search(self.test_dn, '(objectclass=*)',
                                  attributes=['1.1'])
                if not res:
                    ldap_available = False
                    self.skipTest('LDAP server is not available')

                conn.add('ou=UserGroups,%s' % self.test_dn,
                         'organizationalUnit')
                conn.add('ou=Users,%s' % self.test_dn, 'organizationalUnit')
                conn.add(enabled_emulation_dn, 'groupOfNames')

            self.addCleanup(self.delete_test_entry)
        except Exception:
            ldap_available = False
            self.skipTest('LDAP server is not available.')

        url = 'ldap://%s' % self.server_name

        config_fixture_ = self.useFixture(config_fixture.Config())
        config_fixture_.config(
            group='ldap',
            url=url,
            user=self.user_dn,
            password=self.password,
            suffix=self.test_dn,
            use_dumb_member=True,
            user_name_attribute='sn',
            # inetOrgPerson doesn't have a good attribute for enabled.
            user_enabled_emulation=True,
            user_enabled_emulation_dn=enabled_emulation_dn,
        )
        self.useFixture(ldapdb.LDAPDatabase())
