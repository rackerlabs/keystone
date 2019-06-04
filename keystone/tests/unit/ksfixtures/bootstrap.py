# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import fixtures
import testresources

from keystone.cmd import bootstrap
from keystone.common import provider_api


class Bootstrap(fixtures.Fixture):
    """A fixture for bootstrapping keystone.

    This fixture uses the same mechanism that operators invoke when they use
    ``keystone-manage bootstrap`` to populate keystone with domains, projects,
    users, roles, assignments, services, and endpoints.

    """

    def __init__(self):
        super(Bootstrap, self).__init__()

        provider_api.ProviderAPIs._clear_registry_instances()

        bootstrapper = bootstrap.Bootstrapper()
        bootstrapper.admin_password = 'password'
        bootstrapper.admin_username = 'admin'
        bootstrapper.project_name = 'admin'
        bootstrapper.admin_role_name = 'admin'
        bootstrapper.service_name = 'keystone'
        bootstrapper.public_url = 'http://localhost/identity/'

        bootstrapper.bootstrap()

        self.admin_password = bootstrap.admin_password
        self.admin_username = bootstrap.admin_username
        self.project_id = bootstrap.project_id
        self.project_name = bootstrap.project_name
        self.reader_role_id = bootstrap.reader_role_id
        self.reader_role_name = bootstrap.reader_role_name
        self.member_role_id = bootstrap.member_role_id
        self.member_role_name = bootstrap.member_role_name
        self.admin_role_id = bootstrap.admin_role_id
        self.admin_role_name = bootstrap.admin_role_name
        self.default_domain_id = bootstrap.default_domain_id
        self.admin_user_id = bootstrap.admin_user_id


class BootstrapResourceManager(testresources.FixtureResource):

    def __init__(self):
        super(BootstrapResourceManager, self).__init__(Bootstrap())
