# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import uuid

import mock
from testtools import matchers

from keystone import catalog
from keystone.catalog.backends import templated
from keystone import tests
from keystone.tests.ksfixtures import database


def new_endpoint_ref(id, service_id, url):
    return {
        'id': id,
        'name': uuid.uuid4().hex,
        'description': uuid.uuid4().hex,
        'interface': uuid.uuid4().hex[:8],
        'service_id': service_id,
        'url': url,
        'region': uuid.uuid4().hex,
    }


class TestCatalogSubstitutionNotification(object):

    def setUp(self):
        super(TestCatalogSubstitutionNotification, self).setUp()
        self.catalog_api = catalog.Manager()

        self.user_id = uuid.uuid4().hex
        self.tenant_id = uuid.uuid4().hex

        self.service_id = uuid.uuid4().hex
        service = {'id': self.service_id, 'name': uuid.uuid4().hex}
        self.catalog_api.create_service(self.service_id, service)

    def config_overrides(self):
        super(TestCatalogSubstitutionNotification, self).config_overrides()
        self.config_fixture.config(group='catalog', driver=self.BACKEND_DRIVER)

    def _test_for_notifications(self, endpoints, expect_notifications=True):
        for ref in endpoints:
            self.catalog_api.create_endpoint(ref['id'], ref)

        deprecated_func = 'keystone.openstack.common.versionutils.deprecated'
        with mock.patch(deprecated_func) as mock_deprecated:
            self._get_catalog(self.user_id, self.tenant_id)

        if expect_notifications:
            self.assertThat(mock_deprecated()().call_count, matchers.Equals(1))
        else:
            self.assertThat(mock_deprecated()().call_count, matchers.Equals(0))

    def test_for_notifications_with_no_substitutions(self):
        endpoint = new_endpoint_ref(
            id='compute',
            service_id=self.service_id,
            url='http://keystone/endpoint')
        self._test_for_notifications([endpoint], expect_notifications=False)

    def test_for_notifications_with_single_endpoint(self):
        endpoint = new_endpoint_ref(
            id='compute',
            service_id=self.service_id,
            url='http://keystone/$(admin_port)s')
        self._test_for_notifications([endpoint])

    def test_for_notifications_with_multiple_endpoints(self):
        endpoints = [
            new_endpoint_ref(
                id='compute',
                service_id=self.service_id,
                url='http://keystone/$(public_port)s'),
            new_endpoint_ref(
                id='identity',
                service_id=self.service_id,
                url='http://keystone/$(public_port)s'),
        ]
        self._test_for_notifications(endpoints)

    def test_grandfathered_substitutions_are_not_deprecated(self):
        """tenant_id and user_id are not deprecated."""
        endpoints = [
            new_endpoint_ref(
                id='compute',
                service_id=self.service_id,
                url='http://keystone/$(tenant_id)s'),
            new_endpoint_ref(
                id='identity',
                service_id=self.service_id,
                url='http://keystone/$(user_id)s'),
        ]
        self._test_for_notifications(endpoints, expect_notifications=False)


class TestV2CatalogSubstitutionNotificationSQL(
    TestCatalogSubstitutionNotification, tests.TestCase):

    BACKEND_DRIVER = 'keystone.catalog.backends.sql.Catalog'

    def setUp(self):
        self.useFixture(database.Database())
        super(TestV2CatalogSubstitutionNotificationSQL, self).setUp()

    def _get_catalog(self, user_id, tenant_id):
        return self.catalog_api.get_catalog(user_id, tenant_id)


class TestV3CatalogSubstitutionNotificationSQL(
    TestCatalogSubstitutionNotification, tests.TestCase):

    BACKEND_DRIVER = 'keystone.catalog.backends.sql.Catalog'

    def setUp(self):
        self.useFixture(database.Database())
        super(TestV3CatalogSubstitutionNotificationSQL, self).setUp()

    def _get_catalog(self, user_id, tenant_id):
        return self.catalog_api.get_v3_catalog(user_id, tenant_id)


class TemplatedCatalog(templated.Catalog):

    def __init__(self, *args, **kwargs):
        super(TemplatedCatalog, self).__init__(*args, **kwargs)
        self.templates = {
            'RegionOne': {
                'compute': {
                    'publicURL': 'http://localhost:8774/v1.1/bar',
                    'name': "'Compute Service'",
                    'id': '2'
                },
                'identity': {
                    'publicURL': 'http://localhost:5000/v2.0',
                    'name': "'Identity Service'",
                    'id': '1'
                }
            }
        }

    def create_endpoint(self, endpoint_id, endpoint):
        self.templates['RegionOne'][endpoint_id]['publicURL'] = endpoint['url']


class TestV2CatalogSubstitutionNotificationTemplated(
    TestCatalogSubstitutionNotification, tests.TestCase):

    BACKEND_DRIVER = 'keystone.tests.test_catalog.TemplatedCatalog'

    def _get_catalog(self, user_id, tenant_id):
        return self.catalog_api.get_catalog(user_id, tenant_id)
