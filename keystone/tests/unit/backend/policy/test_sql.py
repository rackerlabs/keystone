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

from keystone.common import sql
from keystone.tests.unit.backend import core_sql
from keystone.tests.unit.backend.policy import core


class SQLModelTestCase(core_sql.BaseBackendSqlModels):
    """Test cases to validate the table structure."""

    def test_policy_model(self):
        cols = (('id', sql.String, 64),
                ('blob', sql.JsonBlob, None),
                ('type', sql.String, 255),
                ('extra', sql.JsonBlob, None))

        self.assertExpectedSchema('policy', cols)


class SQLDriverTestCase(core.DriverTestCase,
                        core_sql.BaseBackendSqlTests):

    def _get_driver(self):
        return self.policy_api.driver
