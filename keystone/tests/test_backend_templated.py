# Copyright 2012 OpenStack Foundation
#
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

import os
import uuid

from testtools import matchers

from keystone import tests
from keystone.tests import default_fixtures
from keystone.tests.ksfixtures import database
from keystone.tests import test_backend


DEFAULT_CATALOG_TEMPLATES = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    'default_catalog.templates'))


class TestTemplatedCatalog(tests.TestCase, test_backend.CatalogTests):

    DEFAULT_FIXTURE = {
        'RegionOne': {
            'compute': {
                'adminURL': 'http://localhost:8774/v1.1/bar',
                'publicURL': 'http://localhost:8774/v1.1/bar',
                'internalURL': 'http://localhost:8774/v1.1/bar',
                'name': "'Compute Service'",
                'id': '2'
            },
            'identity': {
                'adminURL': 'http://localhost:35357/v2.0',
                'publicURL': 'http://localhost:5000/v2.0',
                'internalURL': 'http://localhost:35357/v2.0',
                'name': "'Identity Service'",
                'id': '1'
            }
        }
    }

    def setUp(self):
        super(TestTemplatedCatalog, self).setUp()
        self.useFixture(database.Database())
        self.load_backends()
        self.load_fixtures(default_fixtures)

    def config_overrides(self):
        super(TestTemplatedCatalog, self).config_overrides()
        self.config_fixture.config(group='catalog',
                                   template_file=DEFAULT_CATALOG_TEMPLATES)

    def test_get_catalog(self):
        catalog_ref = self.catalog_api.get_catalog('foo', 'bar')
        self.assertDictEqual(catalog_ref, self.DEFAULT_FIXTURE)

    def test_catalog_ignored_malformed_urls(self):
        # both endpoints are in the catalog
        catalog_ref = self.catalog_api.get_catalog('foo', 'bar')
        self.assertEqual(2, len(catalog_ref['RegionOne']))

        region = self.catalog_api.driver.templates['RegionOne']
        region['compute']['adminURL'] = 'http://localhost:8774/v1.1/$(tenant)s'

        # the malformed one has been removed
        catalog_ref = self.catalog_api.get_catalog('foo', 'bar')
        self.assertEqual(1, len(catalog_ref['RegionOne']))

    def test_get_catalog_endpoint_disabled(self):
        self.skipTest("Templated backend doesn't have disabled endpoints")

    def test_get_v3_catalog_endpoint_disabled(self):
        self.skipTest("Templated backend doesn't have disabled endpoints")

    def test_get_v3_catalog(self):
        user_id = uuid.uuid4().hex
        project_id = uuid.uuid4().hex
        catalog_ref = self.catalog_api.get_v3_catalog(user_id, project_id)
        exp_catalog = [
            {'endpoints': [
                {'interface': 'admin',
                 'region': 'RegionOne',
                 'url': 'http://localhost:8774/v1.1/%s' % project_id},
                {'interface': 'public',
                 'region': 'RegionOne',
                 'url': 'http://localhost:8774/v1.1/%s' % project_id},
                {'interface': 'internal',
                 'region': 'RegionOne',
                 'url': 'http://localhost:8774/v1.1/%s' % project_id}],
             'type': 'compute',
             'name': "'Compute Service'",
             'id': '2'},
            {'endpoints': [
                {'interface': 'admin',
                 'region': 'RegionOne',
                 'url': 'http://localhost:35357/v2.0'},
                {'interface': 'public',
                 'region': 'RegionOne',
                 'url': 'http://localhost:5000/v2.0'},
                {'interface': 'internal',
                 'region': 'RegionOne',
                 'url': 'http://localhost:35357/v2.0'}],
             'type': 'identity',
             'name': "'Identity Service'",
             'id': '1'}]
        self.assertEqual(exp_catalog, catalog_ref)

    def test_list_regions_filtered_by_parent_region_id(self):
        self.skipTest('Templated backend does not support hints')

    def test_service_filtering(self):
        self.skipTest("kvs backend doesn't support filtering")

    def test_delete_endpoint(self):
        self.skipTest('Templated backend does not support endpoint deletion')

    def test_delete_endpoint_404(self):
        self.skipTest('Templated backend does not support endpoint deletion')

    def test_endpoint_create(self):
        self.skipTest('Templated backend does not support endpoint creation')

    def test_create_endpoint(self):
        self.skipTest('Templated backend does not support endpoint creation')

    def test_create_endpoint_404(self):
        self.skipTest('Templated backend does not support endpoint creation')

    def test_endpoint_create_with_null_adminurl(self):
        self.skipTest('Templated backend does not support endpoint creation')

    def test_endpoint_create_with_empty_internalurl(self):
        self.skipTest('Templated backend does not support endpoint creation')

    def test_endpoint_create_with_empty_publicurl(self):
        self.skipTest('Templated backend does not support endpoint creation')

    def test_endpoint_create_with_empty_service_id(self):
        self.skipTest('Templated backend does not support endpoint creation')

    def test_delete_service(self):
        self.skipTest('Templated backend does not support service deletion')

    def test_service_delete_404(self):
        self.skipTest('Templated backend does not support service deletion')

    def test_delete_service_404(self):
        self.skipTest('Templated backend does not support service deletion')

    def test_delete_service_with_endpoint(self):
        self.skipTest('Templated backend does not support service deletion')

    def test_cache_layer_delete_service_with_endpoint(self):
        self.skipTest('Templated backend does not support service deletion')

    def test_cache_layer_region_crud(self):
        self.skipTest('Templated backend does not support region CRUD')

    def test_cache_layer_service_crud(self):
        self.skipTest('Templated backend does not support service CRUD')

    def test_service_crud(self):
        # create
        # Templated backend does not support service creation

        # list
        services = self.catalog_api.list_services()
        service_id = '1'
        self.assertIn(service_id, [x['id'] for x in services])

        # delete
        # Templated backend does not support service deletion

    def test_create_region_invalid_parent_region_404(self):
        self.skipTest('Templated backend does not support region creation')

    def test_create_region_with_duplicate_id(self):
        self.skipTest('Templated backend does not support region creation')

    def test_region_crud(self):
        # create
        # Templated backend does not support region creation

        # list
        region_id = 'RegionOne'
        regions = self.catalog_api.list_regions()
        self.assertThat(regions, matchers.HasLength(1))
        region_ids = [x['id'] for x in regions]
        self.assertIn(region_id, region_ids)

        # delete
        # Templated backend does not support region deletion

    def test_delete_region_404(self):
        self.skipTest('Templated backend does not support region deletion')
