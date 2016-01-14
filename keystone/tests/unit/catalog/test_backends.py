# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import uuid

from oslo_config import cfg
from oslo_config import fixture as config_fixture

from keystone import catalog
from keystone.common import dependency
from keystone.tests import unit
from keystone.tests.unit import ksfixtures
from keystone.tests.unit.ksfixtures import database


CONF = cfg.CONF


class BaseCatalogAPITestCases(object):

    def setUp(self):
        self.config_fixture = self.useFixture(config_fixture.Config(CONF))
        self.useFixture(ksfixtures.Cache())

        super(BaseCatalogAPITestCases, self).setUp()

        self.setup_backend()
        self.catalog_api = catalog.Manager()

        self.setup_data()

        self.addCleanup(dependency.reset)

    def setup_backend(self):
        """Override to setup a backend for these test cases."""

    def setup_data(self):
        """Override to setup test data for these test cases."""

    def create_endpoint(self, service_id, **kwargs):
        endpoint = unit.new_endpoint_ref(service_id=service_id,
                                         region_id=None,
                                         **kwargs)
        self.catalog_api.create_endpoint(endpoint['id'], endpoint)
        return endpoint

    def test_get_catalog_ignores_endpoints_with_invalid_urls(self):
        user_id = uuid.uuid4().hex
        tenant_id = uuid.uuid4().hex

        # the only endpoint in the catalog is the one created in setUp
        catalog = self.catalog_api.get_catalog(user_id, tenant_id)
        self.assertEqual(1, len(catalog))
        # it's also the only endpoint in the backend
        self.assertEqual(1, len(self.catalog_api.list_endpoints()))

        # create a new, invalid endpoint - malformed type declaration
        self.create_endpoint(self.service_id,
                             url='http://keystone/%(tenant_id)')

        # create a new, invalid endpoint - nonexistent key
        self.create_endpoint(self.service_id,
                             url='http://keystone/%(you_wont_find_me)s')

        # verify that the invalid endpoints don't appear in the catalog
        catalog = self.catalog_api.get_catalog(user_id, tenant_id)
        self.assertEqual(1, len(catalog))
        # all three endpoints appear in the backend
        self.assertEqual(3, len(self.catalog_api.list_endpoints()))

    def test_get_catalog_always_returns_service_name(self):
        user_id = uuid.uuid4().hex
        tenant_id = uuid.uuid4().hex

        # new_service_ref() returns a ref with a `name`.
        named_svc = unit.new_service_ref()
        self.catalog_api.create_service(named_svc['id'], named_svc)
        self.create_endpoint(service_id=named_svc['id'])

        # This time manually delete the generated `name`.
        unnamed_svc = unit.new_service_ref()
        del unnamed_svc['name']
        self.catalog_api.create_service(unnamed_svc['id'], unnamed_svc)
        self.create_endpoint(service_id=unnamed_svc['id'])

        region = None
        catalog = self.catalog_api.get_catalog(user_id, tenant_id)

        self.assertEqual(named_svc['name'],
                         catalog[region][named_svc['type']]['name'])

        # verify a name is not generated when the service is passed to the API
        self.assertEqual('', catalog[region][unnamed_svc['type']]['name'])


class TestSQLCatalogAPI(BaseCatalogAPITestCases, unit.BaseTestCase):

    def setup_backend(self):
        self.config_fixture.config(group='catalog', driver='sql')
        self.useFixture(database.Database())

    def setup_data(self):
        service = unit.new_service_ref()
        self.service_id = service['id']
        self.catalog_api.create_service(self.service_id, service)
        self.create_endpoint(service_id=self.service_id)


class TestTemplatedCatalogAPI(BaseCatalogAPITestCases, unit.BaseTestCase):

    def setup_backend(self):
        self.config_fixture.config(
            group='catalog',
            driver='templated',
            template_file=unit.dirs.tests('default_catalog.templates'))
