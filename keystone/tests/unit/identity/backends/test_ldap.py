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

from oslo_config import fixture as config_fixture

from keystone.identity.backends import ldap
from keystone.tests.unit import core
from keystone.tests.unit.identity import test_core
from keystone.tests.unit.ksfixtures import ldapdb


class TestIdentityDriver(core.BaseTestCase,
                         test_core.IdentityDriverV8Tests):
    def setUp(self):
        super(TestIdentityDriver, self).setUp()
        self.driver = ldap.Identity()
        self.expected_is_domain_aware = False
        self.expected_default_assignment_driver = 'sql'
        self.expected_is_sql = False
        self.expected_generates_uuids = False

        config_fixture_ = self.useFixture(config_fixture.Config())
        config_fixture_.config(
            group='ldap',
            url='fake://memory',
            user='cn=Admin',
            password='password',
            suffix='cn=example,cn=com')

        self.useFixture(ldapdb.LDAPDatabase())

        self.driver = ldap.Identity()
