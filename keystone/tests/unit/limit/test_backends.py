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

import copy
import uuid

import mock
from six.moves import range
from testtools import matchers

from keystone.catalog.backends import base
from keystone.common import driver_hints
from keystone import exception
from keystone.tests import unit


class LimitTests(object):

    def test_registered_limit_crud(self):
        # create one
        new_registered_limit1 = unit.new_registered_limit_ref(
            service_id=self.service_volumev3, region_id=self.region_RegionOne,
            resource_name='volume', default_limit=10, id=uuid.uuid4().hex)
        res1 = self.registered_limit_api.create_registered_limits(
            [new_registered_limit1])
        self.assertDictEqual(new_registered_limit1, res1[0])

        # create another
        new_registered_limit2 = unit.new_registered_limit_ref(
            service_id=self.service_volumev3, region_id=self.region_RegionOne,
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
            registered_limit_update)
        registered_limit_ids = [re['id'] for re in res]
        self.assertIn(new_registered_limit1['id'], registered_limit_ids)
        self.assertIn(new_registered_limit2['id'], registered_limit_ids)
        regions = [re['region_id'] for re in res]
        self.assertEqual(2, len(regions))
        self.assertIn('RegionOne', regions)
        self.assertIn('RegionTwo', regions)

        # show
        res = self.registered_limit_api.get_registered_limit(
            new_registered_limit1['id'])
        self.assertDictEqual(new_registered_limit1, res)

        # delete
        self.registered_limit_api.delete_registered_limit(
            new_registered_limit1['id'])
        self.assertRaise(exception.RegisteredLimitNotFound,
                         self.registered_limit_api.get_registered_limit,
                         new_registered_limit1['id'])
