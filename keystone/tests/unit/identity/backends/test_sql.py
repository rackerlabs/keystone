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


from keystone.identity.backends import sql
from keystone.tests.unit import core
from keystone.tests.unit.identity import test_core
from keystone.tests.unit.ksfixtures import database


class TestIdentityDriver(core.BaseTestCase,
                         test_core.IdentityDriverV8Tests):
    def setUp(self):
        super(TestIdentityDriver, self).setUp()
        self.expect_is_domain_aware = True
        self.expected_default_assignment_driver = 'sql'
        self.expected_is_sql = True
        self.expected_generates_uuids = True

        self.useFixture(database.Database())

        self.driver = sql.Identity()
