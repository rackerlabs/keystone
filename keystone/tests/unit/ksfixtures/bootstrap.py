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

import sys

import fixtures
import testresources

from keystone.cmd import bootstrap
from keystone.common import provider_api
from keystone import exception
import keystone.server
from keystone.tests.unit import default_fixtures
from keystone.tests.unit import ksfixtures

PROVIDERS = provider_api.ProviderAPIs

class Bootstrap(fixtures.Fixture):
    """A fixture for bootstrapping keystone.

    This fixture uses the same mechanism that operators invoke when they use
    ``keystone-manage bootstrap`` to populate keystone with domains, projects,
    users, roles, assignments, services, and endpoints.

    """

    def setUp(self):
        super(Bootstrap, self).setUp()

        PROVIDERS._clear_registry_instances()

        bootstrapper = bootstrap.Bootstrapper()
        try:
            PROVIDERS.resource_api.create_domain(
                default_fixtures.ROOT_DOMAIN['id'],
                default_fixtures.ROOT_DOMAIN)
        except exception.Conflict:
            pass

        bootstrapper.admin_password = 'password'
        bootstrapper.admin_username = 'admin'
        bootstrapper.project_name = 'admin'
        bootstrapper.admin_role_name = 'admin'
        bootstrapper.service_name = 'keystone'
        bootstrapper.public_url = 'http://localhost/identity/'

        sys.stderr.write("running bootstrap\n")
        bootstrapper.bootstrap()

        self.admin_password = bootstrapper.admin_password
        self.admin_username = bootstrapper.admin_username
        self.project_id = bootstrapper.project_id
        self.project_name = bootstrapper.project_name
        self.reader_role_id = bootstrapper.reader_role_id
        self.reader_role_name = bootstrapper.reader_role_name
        self.member_role_id = bootstrapper.member_role_id
        self.member_role_name = bootstrapper.member_role_name
        self.admin_role_id = bootstrapper.admin_role_id
        self.admin_role_name = bootstrapper.admin_role_name
        self.default_domain_id = bootstrapper.default_domain_id
        self.admin_user_id = bootstrapper.admin_user_id


class BootstrapFixtureResource(testresources.FixtureResource):
    def __init__(self, fixture=None):
        super(BootstrapFixtureResource, self).__init__(ksfixtures.Bootstrap())

    def isDirty(self):
        return self._dirty

    def getResource(self, result=None):
        if not self.isDirty():
            self._setResource(self._make_all(result))
            self._dirty = True
        return self._currentResource

    _dirty = False
