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

from keystone.tests.unit import test_backend_sql


class SqlIdentityV8(test_backend_sql.SqlIdentity):
    """Test that a V8 driver still passes the same tests.

    We use the SQL driver as an example of a V8 legacy driver.

    """

    def config_overrides(self):
        super(SqlIdentityV8, self).config_overrides()
        # V8 SQL specific driver overrides
        self.config_fixture.config(
            group='identity',
            driver='keystone.identity.V8_backends.sql.Identity')
        self.use_specific_sql_driver_version(
            'keystone.identity', 'backends', 'V8_')

    # TODO(henry-nash): Currently the shadow users base driver class will load
    # the non-legacy identity driver - need to find a way of allowing the
    # shadow driver methods access to the legacy driver
    def test_create_federated_user_unique_constraint(self):
        self.skipTest('Legacy testing of cross calling from shadow users to '
                      'user not yet supported')
