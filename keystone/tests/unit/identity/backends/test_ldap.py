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

import ldap3
from oslo_config import fixture as config_fixture

from keystone.identity.backends import ldap
from keystone.tests.unit import core
from keystone.tests.unit.identity import test_core
from keystone.tests.unit.ksfixtures import ldapdb


class TestIdentityDriver(core.BaseTestCase,
                         test_core.IdentityDriverV8Tests):

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


class OpportunisticLiveIdentityDriverTest(TestIdentityDriver):

    def delete_test_entry(self):
        with ldap3.Connection(self.server_name, user=self.user_dn,
                              password=self.password) as conn:
            conn.search(self.test_dn, '(objectclass=*)', attributes=['1.1'])
            dns = sorted((e.entry_get_dn() for e in conn.entries), key=len)
            for dn in dns:
                conn.delete(dn)

    def configure_ldap_server(self):
        # FIXME(blk-u): env vars for all these.
        self.server_name = 'localhost'
        self.user_dn = 'cn=Manager,dc=openstack,dc=org'
        self.password = 'password'
        self.base_dn = 'ou=keystone-test,dc=openstack,dc=org'
        self.enabled_emulation_dn = 'cn=UsersEnabled,%s' % self.base_dn

        self.test_dn = 'ou=%s,%s' % (uuid.uuid4().hex, self.base_dn)

        with ldap3.Connection(self.server_name, user=self.user_dn,
                              password=self.password) as conn:
            conn.add(self.test_dn, 'organizationalUnit')
            conn.add('ou=UserGroups,%s' % self.test_dn, 'organizationalUnit')
            conn.add('ou=Users,%s' % self.test_dn, 'organizationalUnit')
            conn.add(self.enabled_emulation_dn, 'groupOfNames')

        self.addCleanup(self.delete_test_entry)

        url = 'ldap://%s' % self.server_name

        config_fixture_ = self.useFixture(config_fixture.Config())
        config_fixture_.config(
            group='ldap',
            url=url,
            user=self.user_dn,
            password=self.password,
            suffix=self.test_dn,
            use_dumb_member=True,
            user_attribute_ignore=['email', 'tenants', 'default_project_id'],
            user_name_attribute='sn',
            user_enabled_emulation=True,
            user_enabled_emulation_dn=self.enabled_emulation_dn,
        )
        self.useFixture(ldapdb.LDAPDatabase())

        # If any of this fails, do a skipTest on it.
