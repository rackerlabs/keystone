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

from keystone.common import driver_hints
from keystone.common import provider_api
from keystone import exception
from keystone.tests import unit


PROVIDERS = provider_api.ProviderAPIs


class LimitTests(object):

    def test_registered_limit_crud(self):
        # create one
        registered_limit_1 = unit.new_registered_limit_ref(
            service_id=self.service_ServiceOne['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', default_limit=10, id=uuid.uuid4().hex)
        res1 = PROVIDERS.unified_limit_api.create_registered_limits(
            [registered_limit_1])
        self.assertDictEqual(registered_limit_1, res1[0])

        # create another
        registered_limit_2 = unit.new_registered_limit_ref(
            service_id=self.service_ServiceOne['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='snapshot', default_limit=5, id=uuid.uuid4().hex)
        res2 = PROVIDERS.unified_limit_api.create_registered_limits(
            [registered_limit_2])
        self.assertDictEqual(registered_limit_2, res2[0])

        # list
        reg_limits = PROVIDERS.unified_limit_api.list_registered_limits()
        self.assertEqual(2, len(reg_limits))
        registered_limit_ids = [registered_limit['id'] for registered_limit
                                in reg_limits]
        self.assertIn(registered_limit_1['id'], registered_limit_ids)
        self.assertIn(registered_limit_2['id'], registered_limit_ids)

        # update one, return all registered_limits
        registered_limit_update = {'id': registered_limit_1['id'],
                                   'region_id': 'RegionTwo'}
        res = PROVIDERS.unified_limit_api.update_registered_limits(
            [registered_limit_update])
        registered_limit_ids = [re['id'] for re in res]
        self.assertIn(registered_limit_1['id'], registered_limit_ids)
        self.assertIn(registered_limit_2['id'], registered_limit_ids)
        regions = [re['region_id'] for re in res]
        self.assertEqual(2, len(regions))
        self.assertIn('RegionOne', regions)
        self.assertIn('RegionTwo', regions)

        # show
        res = PROVIDERS.unified_limit_api.get_registered_limit(
            registered_limit_2['id'])
        self.assertDictEqual(registered_limit_2, res)

        # delete
        PROVIDERS.unified_limit_api.delete_registered_limit(
            registered_limit_1['id'])
        self.assertRaises(exception.RegisteredLimitNotFound,
                          PROVIDERS.unified_limit_api.get_registered_limit,
                          registered_limit_1['id'])

    def test_create_registered_limit_duplicate(self):
        registered_limit_1 = unit.new_registered_limit_ref(
            service_id=self.service_ServiceOne['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', default_limit=10, id=uuid.uuid4().hex)
        PROVIDERS.unified_limit_api.create_registered_limits(
            [registered_limit_1])

        registered_limit_2 = unit.new_registered_limit_ref(
            service_id=self.service_ServiceOne['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', default_limit=10, id=uuid.uuid4().hex)
        self.assertRaises(exception.Conflict,
                          PROVIDERS.unified_limit_api.create_registered_limits,
                          [registered_limit_2])

    def test_create_multi_registered_limit_duplicate(self):
        registered_limit_1 = unit.new_registered_limit_ref(
            service_id=self.service_ServiceOne['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', default_limit=10, id=uuid.uuid4().hex)
        PROVIDERS.unified_limit_api.create_registered_limits(
            [registered_limit_1])

        # Create with a duplicated one and a normal one. Both of them will not
        # be created.
        registered_limit_2 = unit.new_registered_limit_ref(
            service_id=self.service_ServiceOne['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', default_limit=10, id=uuid.uuid4().hex)
        registered_limit_3 = unit.new_registered_limit_ref(
            service_id=self.service_ServiceOne['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='snapshot', default_limit=10, id=uuid.uuid4().hex)
        self.assertRaises(exception.Conflict,
                          PROVIDERS.unified_limit_api.create_registered_limits,
                          [registered_limit_2, registered_limit_3])

        reg_limits = PROVIDERS.unified_limit_api.list_registered_limits()
        self.assertEqual(1, len(reg_limits))

    def test_create_registered_limit_invalid_service(self):
        registered_limit_1 = unit.new_registered_limit_ref(
            service_id=uuid.uuid4().hex,
            region_id=self.region_RegionOne['id'],
            resource_name='volume', default_limit=10, id=uuid.uuid4().hex)
        self.assertRaises(exception.ValidationError,
                          PROVIDERS.unified_limit_api.create_registered_limits,
                          [registered_limit_1])

    def test_create_registered_limit_invalid_region(self):
        registered_limit_1 = unit.new_registered_limit_ref(
            service_id=self.service_ServiceOne['id'],
            region_id=uuid.uuid4().hex,
            resource_name='volume', default_limit=10, id=uuid.uuid4().hex)
        self.assertRaises(exception.ValidationError,
                          PROVIDERS.unified_limit_api.create_registered_limits,
                          [registered_limit_1])

    def test_update_registered_limit_invalid_input_return_bad_request(self):
        registered_limit_1 = unit.new_registered_limit_ref(
            service_id=self.service_ServiceOne['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', default_limit=10, id=uuid.uuid4().hex)
        PROVIDERS.unified_limit_api.create_registered_limits(
            [registered_limit_1])

        update_ref = {'id': registered_limit_1['id'],
                      'service_id': uuid.uuid4().hex}
        self.assertRaises(exception.ValidationError,
                          PROVIDERS.unified_limit_api.update_registered_limits,
                          [update_ref])

        update_ref = {'id': registered_limit_1['id'],
                      'region_id': 'fake_id'}
        self.assertRaises(exception.ValidationError,
                          PROVIDERS.unified_limit_api.update_registered_limits,
                          [update_ref])

    def test_update_registered_limit_duplicate(self):
        registered_limit_1 = unit.new_registered_limit_ref(
            service_id=self.service_ServiceOne['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', default_limit=10, id=uuid.uuid4().hex)
        registered_limit_2 = unit.new_registered_limit_ref(
            service_id=self.service_ServiceOne['id'],
            region_id=self.region_RegionTwo['id'],
            resource_name='snapshot', default_limit=10, id=uuid.uuid4().hex)
        PROVIDERS.unified_limit_api.create_registered_limits(
            [registered_limit_1, registered_limit_2])

        # Update registered_limit1 to registered_limit2
        update_ref = {'id': registered_limit_1['id'],
                      'region_id': self.region_RegionTwo['id'],
                      'resource_name': 'snapshot'}
        self.assertRaises(exception.Conflict,
                          PROVIDERS.unified_limit_api.update_registered_limits,
                          [update_ref])

    def test_list_registered_limit_by_filter(self):
        registered_limit_1 = unit.new_registered_limit_ref(
            service_id=self.service_ServiceOne['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', default_limit=10, id=uuid.uuid4().hex)
        registered_limit_2 = unit.new_registered_limit_ref(
            service_id=self.service_ServiceOne['id'],
            region_id=self.region_RegionTwo['id'],
            resource_name='snapshot', default_limit=10, id=uuid.uuid4().hex)
        PROVIDERS.unified_limit_api.create_registered_limits(
            [registered_limit_1, registered_limit_2])

        hints = driver_hints.Hints()
        hints.add_filter('service_id', self.service_ServiceOne['id'])
        res = PROVIDERS.unified_limit_api.list_registered_limits(hints)
        self.assertEqual(2, len(res))

        hints = driver_hints.Hints()
        hints.add_filter('region_id', self.region_RegionOne['id'])
        res = PROVIDERS.unified_limit_api.list_registered_limits(hints)
        self.assertEqual(1, len(res))

        hints = driver_hints.Hints()
        hints.add_filter('resource_name', 'backup')
        res = PROVIDERS.unified_limit_api.list_registered_limits(hints)
        self.assertEqual(0, len(res))

    def test_get_registered_limit_returns_not_found(self):
        self.assertRaises(exception.RegisteredLimitNotFound,
                          PROVIDERS.unified_limit_api.get_registered_limit,
                          uuid.uuid4().hex)

    def test_delete_registered_limit_returns_not_found(self):
        self.assertRaises(exception.RegisteredLimitNotFound,
                          PROVIDERS.unified_limit_api.delete_registered_limit,
                          uuid.uuid4().hex)

    def _create_default_registered_limits(self):
        registered_limit_1 = unit.new_registered_limit_ref(
            service_id=self.service_ServiceOne['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', default_limit=10, id=uuid.uuid4().hex)
        registered_limit_2 = unit.new_registered_limit_ref(
            service_id=self.service_ServiceOne['id'],
            region_id=self.region_RegionTwo['id'],
            resource_name='snapshot', default_limit=10, id=uuid.uuid4().hex)
        PROVIDERS.unified_limit_api.create_registered_limits(
            [registered_limit_1, registered_limit_2])

    def test_limit_crud(self):
        self._create_default_registered_limits()
        # create one
        limit_1 = unit.new_limit_ref(
            project_id=self.tenant_bar['id'],
            service_id=self.service_ServiceOne['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', resource_limit=10, id=uuid.uuid4().hex)
        res1 = PROVIDERS.unified_limit_api.create_limits([limit_1])
        self.assertDictEqual(limit_1, res1[0])

        # create another
        limit_2 = unit.new_limit_ref(
            project_id=self.tenant_bar['id'],
            service_id=self.service_ServiceOne['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='snapshot', resource_limit=5, id=uuid.uuid4().hex)
        res2 = PROVIDERS.unified_limit_api.create_limits([limit_2])
        self.assertDictEqual(limit_2, res2[0])

        # list
        limits = PROVIDERS.unified_limit_api.list_limits(None,
                                                         self.tenant_bar['id'])
        self.assertEqual(2, len(limits))
        limit_ids = [limit['id'] for limit in limits]
        self.assertIn(limit_1['id'], limit_ids)
        self.assertIn(limit_2['id'], limit_ids)

        # update one, return all limits
        limit_update = {'id': limit_1['id'],
                        'resource_limit': 8}
        res = PROVIDERS.unified_limit_api.update_limits([limit_update],
                                                        self.tenant_bar['id'])
        limit_ids = [re['id'] for re in res]
        self.assertIn(limit_1['id'], limit_ids)
        self.assertIn(limit_2['id'], limit_ids)
        resource_limit = [re['resource_limit'] for re in res]
        self.assertEqual(2, len(resource_limit))
        self.assertIn(8, resource_limit)
        self.assertIn(5, resource_limit)

        # show
        res = PROVIDERS.unified_limit_api.get_limit(limit_2['id'])
        self.assertDictEqual(limit_2, res)

        # delete
        PROVIDERS.unified_limit_api.delete_limit(limit_1['id'])
        self.assertRaises(exception.LimitNotFound,
                          PROVIDERS.unified_limit_api.get_limit,
                          limit_1['id'])

    def test_create_limit_duplicate(self):
        self._create_default_registered_limits()
        limit_1 = unit.new_limit_ref(
            project_id=self.tenant_bar['id'],
            service_id=self.service_ServiceOne['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', resource_limit=10, id=uuid.uuid4().hex)
        PROVIDERS.unified_limit_api.create_limits([limit_1])

        # use different id
        limit_1 = unit.new_limit_ref(
            project_id=self.tenant_bar['id'],
            service_id=self.service_ServiceOne['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', resource_limit=10, id=uuid.uuid4().hex)
        self.assertRaises(exception.Conflict,
                          PROVIDERS.unified_limit_api.create_limits,
                          [limit_1])

    def test_create_limit_invalid_input_returns_bad_request(self):
        limit_1 = unit.new_limit_ref(
            project_id=self.tenant_bar['id'],
            service_id=uuid.uuid4().hex,
            region_id=self.region_RegionOne['id'],
            resource_name='volume', resource_limit=10, id=uuid.uuid4().hex)
        self.assertRaises(exception.ValidationError,
                          PROVIDERS.unified_limit_api.create_limits,
                          [limit_1])

        limit_1 = unit.new_limit_ref(
            project_id=self.tenant_bar['id'],
            service_id=self.service_ServiceOne['id'],
            region_id=uuid.uuid4().hex,
            resource_name='volume', resource_limit=10, id=uuid.uuid4().hex)
        self.assertRaises(exception.ValidationError,
                          PROVIDERS.unified_limit_api.create_limits,
                          [limit_1])

    def test_list_limit_by_filter(self):
        limit_1 = unit.new_limit_ref(
            project_id=self.tenant_bar['id'],
            service_id=self.service_ServiceOne['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', resource_limit=10, id=uuid.uuid4().hex)
        limit_2 = unit.new_limit_ref(
            project_id=self.tenant_bar['id'],
            service_id=self.service_ServiceOne['id'],
            region_id=self.region_RegionTwo['id'],
            resource_name='snapshot', resource_limit=10, id=uuid.uuid4().hex)
        PROVIDERS.unified_limit_api.create_limits([limit_1, limit_2])

        hints = driver_hints.Hints()
        hints.add_filter('service_id', self.service_ServiceOne['id'])
        res = PROVIDERS.unified_limit_api.list_limits(hints,
                                                      self.tenant_bar['id'])
        self.assertEqual(2, len(res))

        hints = driver_hints.Hints()
        hints.add_filter('region_id', self.region_RegionOne['id'])
        res = PROVIDERS.unified_limit_api.list_limits(hints,
                                                      self.tenant_bar['id'])
        self.assertEqual(1, len(res))

        hints = driver_hints.Hints()
        hints.add_filter('resource_name', 'backup')
        res = PROVIDERS.unified_limit_api.list_limits(hints,
                                                      self.tenant_bar['id'])
        self.assertEqual(0, len(res))

    def test_get_limit_returns_not_found(self):
        self.assertRaises(exception.LimitNotFound,
                          PROVIDERS.unified_limit_api.get_limit,
                          uuid.uuid4().hex)

    def test_delete_limit_returns_not_found(self):
        self.assertRaises(exception.LimitNotFound,
                          PROVIDERS.unified_limit_api.delete_limit,
                          uuid.uuid4().hex)
