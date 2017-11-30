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
from keystone import exception
from keystone.tests import unit


class LimitTests(object):

    def test_registered_limit_crud(self):
        # create one
        new_registered_limit1 = unit.new_registered_limit_ref(
            service_id=self.service_volumev3['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', default_limit=10, id=uuid.uuid4().hex)
        res1 = self.registered_limit_api.create_registered_limits(
            [new_registered_limit1])
        self.assertDictEqual(new_registered_limit1, res1[0])

        # create another
        new_registered_limit2 = unit.new_registered_limit_ref(
            service_id=self.service_volumev3['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='snapshot', default_limit=5, id=uuid.uuid4().hex)
        res2 = self.registered_limit_api.create_registered_limits(
            [new_registered_limit2])
        self.assertDictEqual(new_registered_limit2, res2[0])

        # list
        registered_limits = self.registered_limit_api.list_registered_limits()
        self.assertEqual(2, len(registered_limits))
        registered_limit_ids = [registered_limit['id'] for registered_limit
                                in registered_limits]
        self.assertIn(new_registered_limit1['id'], registered_limit_ids)
        self.assertIn(new_registered_limit2['id'], registered_limit_ids)

        # update one, return all registered_limits
        registered_limit_update = {'id': new_registered_limit1['id'],
                                   'region_id': 'RegionTwo'}
        res = self.registered_limit_api.update_registered_limits(
            [registered_limit_update])
        registered_limit_ids = [re['id'] for re in res]
        self.assertIn(new_registered_limit1['id'], registered_limit_ids)
        self.assertIn(new_registered_limit2['id'], registered_limit_ids)
        regions = [re['region_id'] for re in res]
        self.assertEqual(2, len(regions))
        self.assertIn('RegionOne', regions)
        self.assertIn('RegionTwo', regions)

        # show
        res = self.registered_limit_api.get_registered_limit(
            new_registered_limit2['id'])
        self.assertDictEqual(new_registered_limit2, res)

        # delete
        self.registered_limit_api.delete_registered_limit(
            new_registered_limit1['id'])
        self.assertRaises(exception.RegisteredLimitNotFound,
                          self.registered_limit_api.get_registered_limit,
                          new_registered_limit1['id'])

    def test_create_registered_limit_duplicate(self):
        new_registered_limit1 = unit.new_registered_limit_ref(
            service_id=self.service_volumev3['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', default_limit=10, id=uuid.uuid4().hex)
        self.registered_limit_api.create_registered_limits(
            [new_registered_limit1])

        # use different id
        new_registered_limit1 = unit.new_registered_limit_ref(
            service_id=self.service_volumev3['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', default_limit=10, id=uuid.uuid4().hex)
        self.assertRaises(exception.Conflict,
                          self.registered_limit_api.create_registered_limits,
                          [new_registered_limit1])

    def test_create_registered_limit_invalid_input_returns_bad_request(self):
        new_registered_limit1 = unit.new_registered_limit_ref(
            service_id=uuid.uuid4().hex,
            region_id=self.region_RegionOne['id'],
            resource_name='volume', default_limit=10, id=uuid.uuid4().hex)
        self.assertRaises(exception.ValidationError,
                          self.registered_limit_api.create_registered_limits,
                          [new_registered_limit1])

        new_registered_limit1 = unit.new_registered_limit_ref(
            service_id=self.service_volumev3['id'],
            region_id=uuid.uuid4().hex,
            resource_name='volume', default_limit=10, id=uuid.uuid4().hex)
        self.assertRaises(exception.ValidationError,
                          self.registered_limit_api.create_registered_limits,
                          [new_registered_limit1])

    def test_update_registered_limit_invalid_input_return_bad_request(self):
        new_registered_limit1 = unit.new_registered_limit_ref(
            service_id=self.service_volumev3['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', default_limit=10, id=uuid.uuid4().hex)
        self.registered_limit_api.create_registered_limits(
            [new_registered_limit1])

        update_ref = {'id': new_registered_limit1['id'],
                      'service_id': uuid.uuid4().hex}
        self.assertRaises(exception.ValidationError,
                          self.registered_limit_api.update_registered_limits,
                          [update_ref])

        update_ref = {'id': new_registered_limit1['id'],
                      'region_id': 'fake_id'}
        self.assertRaises(exception.ValidationError,
                          self.registered_limit_api.update_registered_limits,
                          [update_ref])

    def test_update_registered_limit_duplicate(self):
        new_registered_limit1 = unit.new_registered_limit_ref(
            service_id=self.service_volumev3['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', default_limit=10, id=uuid.uuid4().hex)
        new_registered_limit2 = unit.new_registered_limit_ref(
            service_id=self.service_volumev3['id'],
            region_id=self.region_RegionTwo['id'],
            resource_name='snapshot', default_limit=10, id=uuid.uuid4().hex)
        self.registered_limit_api.create_registered_limits(
            [new_registered_limit1, new_registered_limit2])

        # Update registered_limit1 to registered_limit2
        update_ref = {'id': new_registered_limit1['id'],
                      'region_id': self.region_RegionTwo['id'],
                      'resource_name': 'snapshot'}
        self.assertRaises(exception.Conflict,
                          self.registered_limit_api.update_registered_limits,
                          [update_ref])

    def test_list_registered_limit_by_filter(self):
        new_registered_limit1 = unit.new_registered_limit_ref(
            service_id=self.service_volumev3['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', default_limit=10, id=uuid.uuid4().hex)
        new_registered_limit2 = unit.new_registered_limit_ref(
            service_id=self.service_volumev3['id'],
            region_id=self.region_RegionTwo['id'],
            resource_name='snapshot', default_limit=10, id=uuid.uuid4().hex)
        self.registered_limit_api.create_registered_limits(
            [new_registered_limit1, new_registered_limit2])

        hints = driver_hints.Hints()
        hints.add_filter('service_id', self.service_volumev3['id'])
        res = self.registered_limit_api.list_registered_limits(hints)
        self.assertEqual(2, len(res))

        hints = driver_hints.Hints()
        hints.add_filter('region_id', self.region_RegionOne['id'])
        res = self.registered_limit_api.list_registered_limits(hints)
        self.assertEqual(1, len(res))

        hints = driver_hints.Hints()
        hints.add_filter('resource_name', 'backup')
        res = self.registered_limit_api.list_registered_limits(hints)
        self.assertEqual(0, len(res))

    def test_get_registered_limit_returns_not_found(self):
        self.assertRaises(exception.RegisteredLimitNotFound,
                          self.registered_limit_api.get_registered_limit,
                          uuid.uuid4().hex)

    def test_delete_registered_limit_returns_not_found(self):
        self.assertRaises(exception.RegisteredLimitNotFound,
                          self.registered_limit_api.delete_registered_limit,
                          uuid.uuid4().hex)

    def _create_default_registered_limits(self):
        new_registered_limit1 = unit.new_registered_limit_ref(
            service_id=self.service_volumev3['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', default_limit=10, id=uuid.uuid4().hex)
        new_registered_limit2 = unit.new_registered_limit_ref(
            service_id=self.service_volumev3['id'],
            region_id=self.region_RegionTwo['id'],
            resource_name='snapshot', default_limit=10, id=uuid.uuid4().hex)
        self.registered_limit_api.create_registered_limits(
            [new_registered_limit1, new_registered_limit2])

    def test_limit_crud(self):
        self._create_default_registered_limits()
        # create one
        new_limit1 = unit.new_limit_ref(
            project_id=self.tenant_bar['id'],
            service_id=self.service_volumev3['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', resource_limit=10, id=uuid.uuid4().hex)
        res1 = self.limit_api.create_limits([new_limit1])
        self.assertDictEqual(new_limit1, res1[0])

        # create another
        new_limit2 = unit.new_limit_ref(
            project_id=self.tenant_bar['id'],
            service_id=self.service_volumev3['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='snapshot', resource_limit=5, id=uuid.uuid4().hex)
        res2 = self.limit_api.create_limits([new_limit2])
        self.assertDictEqual(new_limit2, res2[0])

        # list
        limits = self.limit_api.list_limits(None, self.tenant_bar['id'])
        self.assertEqual(2, len(limits))
        limit_ids = [limit['id'] for limit in limits]
        self.assertIn(new_limit1['id'], limit_ids)
        self.assertIn(new_limit2['id'], limit_ids)

        # update one, return all limits
        limit_update = {'id': new_limit1['id'],
                        'resource_limit': 8}
        res = self.limit_api.update_limits([limit_update],
                                           self.tenant_bar['id'])
        limit_ids = [re['id'] for re in res]
        self.assertIn(new_limit1['id'], limit_ids)
        self.assertIn(new_limit2['id'], limit_ids)
        resource_limit = [re['resource_limit'] for re in res]
        self.assertEqual(2, len(resource_limit))
        self.assertIn(8, resource_limit)
        self.assertIn(5, resource_limit)

        # show
        res = self.limit_api.get_limit(new_limit2['id'])
        self.assertDictEqual(new_limit2, res)

        # delete
        self.limit_api.delete_limit(new_limit1['id'])
        self.assertRaises(exception.LimitNotFound,
                          self.limit_api.get_limit,
                          new_limit1['id'])

    def test_create_limit_duplicate(self):
        self._create_default_registered_limits()
        new_limit1 = unit.new_limit_ref(
            project_id=self.tenant_bar['id'],
            service_id=self.service_volumev3['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', resource_limit=10, id=uuid.uuid4().hex)
        self.limit_api.create_limits([new_limit1])

        # use different id
        new_limit1 = unit.new_limit_ref(
            project_id=self.tenant_bar['id'],
            service_id=self.service_volumev3['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', resource_limit=10, id=uuid.uuid4().hex)
        self.assertRaises(exception.Conflict,
                          self.limit_api.create_limits,
                          [new_limit1])

    def test_create_limit_invalid_input_returns_bad_request(self):
        new_limit1 = unit.new_limit_ref(
            project_id=self.tenant_bar['id'],
            service_id=uuid.uuid4().hex,
            region_id=self.region_RegionOne['id'],
            resource_name='volume', resource_limit=10, id=uuid.uuid4().hex)
        self.assertRaises(exception.ValidationError,
                          self.limit_api.create_limits,
                          [new_limit1])

        new_limit1 = unit.new_limit_ref(
            project_id=self.tenant_bar['id'],
            service_id=self.service_volumev3['id'],
            region_id=uuid.uuid4().hex,
            resource_name='volume', resource_limit=10, id=uuid.uuid4().hex)
        self.assertRaises(exception.ValidationError,
                          self.limit_api.create_limits,
                          [new_limit1])

    def test_list_limit_by_filter(self):
        new_limit1 = unit.new_limit_ref(
            project_id=self.tenant_bar['id'],
            service_id=self.service_volumev3['id'],
            region_id=self.region_RegionOne['id'],
            resource_name='volume', resource_limit=10, id=uuid.uuid4().hex)
        new_limit2 = unit.new_limit_ref(
            project_id=self.tenant_bar['id'],
            service_id=self.service_volumev3['id'],
            region_id=self.region_RegionTwo['id'],
            resource_name='snapshot', resource_limit=10, id=uuid.uuid4().hex)
        self.limit_api.create_limits([new_limit1, new_limit2])

        hints = driver_hints.Hints()
        hints.add_filter('service_id', self.service_volumev3['id'])
        res = self.limit_api.list_limits(hints, self.tenant_bar['id'])
        self.assertEqual(2, len(res))

        hints = driver_hints.Hints()
        hints.add_filter('region_id', self.region_RegionOne['id'])
        res = self.limit_api.list_limits(hints, self.tenant_bar['id'])
        self.assertEqual(1, len(res))

        hints = driver_hints.Hints()
        hints.add_filter('resource_name', 'backup')
        res = self.limit_api.list_limits(hints, self.tenant_bar['id'])
        self.assertEqual(0, len(res))

    def test_get_limit_returns_not_found(self):
        self.assertRaises(exception.LimitNotFound,
                          self.limit_api.get_limit,
                          uuid.uuid4().hex)

    def test_delete_limit_returns_not_found(self):
        self.assertRaises(exception.LimitNotFound,
                          self.limit_api.delete_limit,
                          uuid.uuid4().hex)
