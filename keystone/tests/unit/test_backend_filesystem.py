# Copyright 2018 Huawei Technologies Co., Ltd.
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

import uuid
import yaml

import mock
from six.moves import zip

from keystone.catalog.backends import base as catalog_base
from keystone.common import provider_api
from keystone.tests import unit
from keystone.tests.unit.catalog import test_backends as catalog_tests
from keystone.tests.unit import default_fixtures
from keystone.tests.unit.ksfixtures import database
from keystone.tests.unit.ksfixtures import temporaryfile


PROVIDERS = provider_api.ProviderAPIs
WRITE_FUNCTIONALITY_MSG = ("Filesystem backend doesn't support write "
                           "operations")


class TestFileSystemCatalog(unit.TestCase, catalog_tests.CatalogTests):

    ENDPOINT_IDs = {'endpoint_id_1': uuid.uuid5(uuid.NAMESPACE_URL,
                                                '%(id)s-%(type)s' % {
                                                    'id': 'EndpointOne',
                                                    'type': 'public'}).hex,
                    'endpoint_id_2': uuid.uuid5(uuid.NAMESPACE_URL,
                                                '%(id)s-%(type)s' % {
                                                    'id': 'EndpointOne',
                                                    'type': 'internal'}).hex,
                    'endpoint_id_3': uuid.uuid5(uuid.NAMESPACE_URL,
                                                '%(id)s-%(type)s' % {
                                                    'id': 'EndpointOne',
                                                    'type': 'admin'}).hex,
                    'endpoint_id_4': uuid.uuid5(uuid.NAMESPACE_URL,
                                                '%(id)s-%(type)s' % {
                                                    'id': 'EndpointOne',
                                                    'type': 'other'}).hex,
                    'endpoint_id_5': uuid.uuid5(uuid.NAMESPACE_URL,
                                                '%(id)s-%(type)s' % {
                                                    'id': 'EndpointTwo',
                                                    'type': 'public'}).hex,
                    'endpoint_id_6': uuid.uuid5(uuid.NAMESPACE_URL,
                                                '%(id)s-%(type)s' % {
                                                    'id': 'EndpointThree',
                                                    'type': 'public'}).hex
                    }

    def setUp(self):
        super(TestFileSystemCatalog, self).setUp()
        self.useFixture(database.Database())
        self.load_backends()
        self.load_fixtures(default_fixtures)

    def config_overrides(self):
        super(TestFileSystemCatalog, self).config_overrides()
        self.config_fixture.config(
            group='catalog',
            driver='filesystem',
            catalog_file=unit.dirs.tests('default_filesystem_catalog.yaml'))

    def _assert_catalogs_equal(self, expected, observed):
        sort_key = lambda d: d['id']
        for e, o in zip(sorted(expected, key=sort_key),
                        sorted(observed, key=sort_key)):
            expected_endpoints = e.pop('endpoints')
            observed_endpoints = o.pop('endpoints')
            self.assertDictEqual(e, o)
            self.assertItemsEqual(expected_endpoints, observed_endpoints)

    def test_get_v3_catalog(self):
        user_id = uuid.uuid4().hex
        project_id = uuid.uuid4().hex
        catalog_ref = PROVIDERS.catalog_api.get_v3_catalog(user_id, project_id)
        exp_catalog = [
            {'endpoints':
                [{'interface': 'public',
                  'url': 'https://identity.example.com',
                  'region': 'RegionOne',
                  'id': self.ENDPOINT_IDs['endpoint_id_1']},
                 {'interface': 'internal',
                  'url': 'https://internal-indentity.example.com',
                  'region': 'RegionOne',
                  'id': self.ENDPOINT_IDs['endpoint_id_2']},
                 {'interface': 'admin',
                  'url': 'https://admin-identity.example.com',
                  'region': 'RegionOne',
                  'id': self.ENDPOINT_IDs['endpoint_id_3']},
                 {'interface': 'other',
                  'url': 'https://something-else-identity.example.com',
                  'region': 'RegionOne',
                  'id': self.ENDPOINT_IDs['endpoint_id_4']}],
             'type': 'identity',
             'id': 'ServiceOne',
             'name': 'ServiceOne'},
            {'endpoints':
                [{'interface': 'public',
                  'url': 'https://compute.example.com/v2.1/',
                  'region': 'RegionOne',
                  'id': self.ENDPOINT_IDs['endpoint_id_5']}],
             'type': 'compute',
             'id': 'ServiceTwo',
             'name': 'ServiceTwo'},
            {'endpoints':
                [{'interface': 'public',
                  'url': 'https://volume.example.com/v2/%s' % project_id,
                  'region': 'RegionOne',
                  'id': self.ENDPOINT_IDs['endpoint_id_6']}],
             'type': 'volume',
             'id': 'ServiceThree',
             'name': 'ServiceThree'}
        ]

        self._assert_catalogs_equal(exp_catalog, catalog_ref)

    def test_list_services(self):
        expect_services = [
            {'enabled': True,
             'id': 'ServiceOne',
             'name': 'ServiceOne',
             'type': 'identity'},
            {'enabled': True,
             'id': 'ServiceTwo',
             'name': 'ServiceTwo',
             'type': 'compute'},
            {'enabled': True,
             'id': 'ServiceThree',
             'name': 'ServiceThree',
             'type': 'volume'}]
        services = PROVIDERS.catalog_api.list_services()
        self.assertEqual(expect_services.sort(key=lambda svc: svc['id']),
                         services.sort(key=lambda svc: svc['id']))

    def test_get_service(self):
        expect_service = {'enabled': True,
                          'id': 'ServiceOne',
                          'name': 'ServiceOne',
                          'type': 'identity'}
        service = PROVIDERS.catalog_api.get_service('ServiceOne')
        self.assertEqual(expect_service, service)

    def test_list_regions(self):
        expect_regions = [
            {'description': '',
             'id': 'RegionOne',
             'parent_region_id': None},
            {'description': 'Second Region',
             'id': 'RegionTwo',
             'parent_region_id': 'RegionOne'}]
        regions = PROVIDERS.catalog_api.list_regions()
        self.assertEqual(expect_regions.sort(key=lambda region: region['id']),
                         regions.sort(key=lambda region: region['id']))

    def test_get_region(self):
        expect_region = {
            'description': 'Second Region',
            'id': 'RegionTwo',
            'parent_region_id': 'RegionOne'}
        region = PROVIDERS.catalog_api.get_region('RegionTwo')
        self.assertEqual(expect_region, region)

    def test_list_endpoints(self):
        expected_urls = set(['https://admin-identity.example.com',
                             'https://compute.example.com/v2.1/',
                             'https://identity.example.com',
                             'https://internal-indentity.example.com',
                             'https://something-else-identity.example.com',
                             'https://volume.example.com/v2/$(project_id)s'])

        endpoints = PROVIDERS.catalog_api.list_endpoints()
        self.assertEqual(expected_urls, set([e['url'] for e in endpoints]))

    def test_get_endpoint(self):
        expect_endpoint = {'enabled': True,
                           'id': self.ENDPOINT_IDs['endpoint_id_1'],
                           'interface': 'public',
                           'legacy_endpoint_id': 'EndpointOne',
                           'region_id': 'RegionOne',
                           'service_id': 'ServiceOne',
                           'url': 'https://identity.example.com'}
        endpoint = PROVIDERS.catalog_api.get_endpoint(
            self.ENDPOINT_IDs['endpoint_id_1'])
        self. assertEqual(expect_endpoint, endpoint)

    def test_get_v3_catalog_endpoint_disabled(self):
        self.skip_test_overrides(
            "Filesystem backend doesn't have disabled endpoints")

    def test_list_regions_filtered_by_parent_region_id(self):
        self.skip_test_overrides('Filesystem backend does not support hints')

    def test_service_filtering(self):
        self.skip_test_overrides("Filesystem backend doesn't support filter")

    # Filesystem backend is readonly so that skip the tests below.

    def test_region_crud(self):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)

    def test_update_region_extras(self):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)

    @unit.skip_if_cache_disabled('catalog')
    def test_cache_layer_region_crud(self):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)

    @unit.skip_if_cache_disabled('catalog')
    def test_invalidate_cache_when_updating_region(self):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)

    def test_create_region_with_duplicate_id(self):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)

    def test_delete_region_returns_not_found(self):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)

    def test_create_region_invalid_parent_region_returns_not_found(self):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)

    def test_avoid_creating_circular_references_in_regions_update(self):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)

    @mock.patch.object(catalog_base.CatalogDriverBase,
                       "_ensure_no_circle_in_hierarchical_regions")
    def test_circular_regions_can_be_deleted(self, mock_ensure_on_circle):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)

    def test_service_crud(self):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)

    @unit.skip_if_cache_disabled('catalog')
    def test_cache_layer_service_crud(self):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)

    @unit.skip_if_cache_disabled('catalog')
    def test_invalidate_cache_when_updating_service(self):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)

    def test_delete_service_with_endpoint(self):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)

    def test_cache_layer_delete_service_with_endpoint(self):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)

    def test_delete_service_returns_not_found(self):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)

    def test_update_endpoint_nonexistent_service(self):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)

    def test_create_endpoint_nonexistent_region(self):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)

    def test_update_endpoint_nonexistent_region(self):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)

    def test_delete_endpoint_returns_not_found(self):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)

    def test_create_endpoint(self):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)

    def test_update_endpoint(self):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)

    @unit.skip_if_cache_disabled('catalog')
    def test_invalidate_cache_when_updating_endpoint(self):
        self.skip_test_overrides(WRITE_FUNCTIONALITY_MSG)


class TestFileSystemCatalogRefreshFile(TestFileSystemCatalog):
    def setUp(self):
        self.tempfile = self.useFixture(temporaryfile.SecureTempFile())
        self.tmpfilename = self.tempfile.file_name
        with open(self.tmpfilename, 'w') as catalog_file:
            with open(unit.dirs.tests('default_filesystem_catalog.yaml'),
                      'r') as default_file:
                catalog_file.write(default_file.read())
        super(TestFileSystemCatalogRefreshFile, self).setUp()

    def config_overrides(self):
        super(TestFileSystemCatalog, self).config_overrides()
        self.config_fixture.config(
            group='catalog',
            driver='filesystem',
            catalog_file=unit.dirs.tests(self.tmpfilename),
            caching=False)

    def test_catalog_file_refresh(self):
        expect_service = {'enabled': True,
                          'id': 'ServiceOne',
                          'name': 'ServiceOne',
                          'type': 'identity'}
        service = PROVIDERS.catalog_api.get_service('ServiceOne')
        self.assertEqual(expect_service, service)

        with open(self.tmpfilename, 'r+') as catalog_file:
            yaml_data = yaml.safe_load(catalog_file)
            yaml_data['services']['ServiceOne']['type'] = 'new_identity'
            catalog_file.write(yaml.dump(yaml_data))

        service = PROVIDERS.catalog_api.get_service('ServiceOne')
        self.assertEqual('new_identity', service['type'])
