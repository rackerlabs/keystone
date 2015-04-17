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

from oslo_config import cfg

from keystone import exception
from keystone.tests import unit
from keystone.tests.unit import test_backend_sql


CONF = cfg.CONF
DEFAULT_DOMAIN_ID = CONF.identity.default_domain_id


class SqlIdentityV8(test_backend_sql.SqlIdentity):
    """Test that a V8 driver still passes the same tests.

    We use the SQL driver as an example of a V8 legacy driver.

    """

    def config_overrides(self):
        super(SqlIdentityV8, self).config_overrides()
        # V8 SQL specific driver overrides
        self.config_fixture.config(
            group='resource',
            driver='keystone.resource.V8_backends.sql.Resource')
        self.use_specific_sql_driver_version(
            'keystone.resource', 'backends', 'V8_')

    def test_get_project_by_name_without_passing_domain_id(self):
        """Tests get_project_by_name with no domain_id provided."""
        project = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID,
                                       is_domain=False)
        self.resource_api.create_project(project['id'], project)

        self.assertRaises(exception.ValidationError,
                          self.resource_api.get_project_by_name,
                          project['name'],
                          None,
                          False)

        # Querying without passing the domain_id is only supported for
        # projects that act as domains in the V9 driver.
        project2 = unit.new_project_ref(domain_id=DEFAULT_DOMAIN_ID,
                                        is_domain=True)
        self.resource_api.create_project(project2['id'], project2)

        self.assertRaises(exception.ProjectNotFound,
                          self.resource_api.get_project_by_name,
                          project2['name'],
                          None,
                          True)
