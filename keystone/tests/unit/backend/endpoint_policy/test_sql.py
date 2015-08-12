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

import itertools
import uuid

from keystone import exception
from keystone.common import sql
from keystone.tests.unit import utils
from keystone.tests.unit.backend import core_sql
from keystone.endpoint_policy.backends.sql import PolicyAssociation


class ModelTestCase(core_sql.BaseBackendSqlModels):
    """Test cases to validate the table structure."""

    def test_policy_association_model(self):
        cols = (('id', sql.String, 64),
                ('policy_id', sql.String, 64),
                ('endpoint_id', sql.String, 64),
                ('service_id', sql.String, 64),
                ('region_id', sql.String, 64))

        self.assertExpectedSchema('policy_association', cols)


class DriverTestCase(core_sql.BaseBackendSqlTests):
    """Test cases to validate the driver handling of the table."""

    def setUp(self):
        super(DriverTestCase, self).setUp()

        self.driver = self.endpoint_policy_api.driver

    def _list_target_combinations(self):
        targets = [{'endpoint_id': uuid.uuid4().hex},
                   {'service_id': uuid.uuid4().hex},
                   {'region_id': uuid.uuid4().hex}]

        for length in range(1, len(targets) + 1):
            for target in itertools.combinations(targets, length):
                yield dict(j for i in target for j in i.items())

    def test_create_policy_association(self):
        for target in self._list_target_combinations():
            association = {'policy_id': uuid.uuid4().hex}
            association.update(target)

            self.driver.create_policy_association(**association)
            self.driver.get_policy_association(**target)

    @utils.wip("Blocked by bug #1483375, the last statement (assertEqual) is "
               "going to fail since the returned value is a tuple")
    def test_create_duplicate_policy_association(self):
        for target in self._list_target_combinations():
            association = {'policy_id': uuid.uuid4().hex}
            association.update(target)

            self.driver.create_policy_association(**association)
            self.driver.get_policy_association(**target)

            new_association = association.copy()
            new_association.update({'policy_id': uuid.uuid4().hex})

            self.driver.create_policy_association(**new_association)
            ret = self.driver.get_policy_association(**target)

            self.assertEqual(new_association['policy_id'], ret['policy_id'])

    def test_check_policy_association(self):
        pass

    def test_delete_policy_association(self):
        pass

    def test_get_policy_association(self):
        pass

    def test_list_associations_for_policy(self):
        pass

    def test_delete_association_by_endpoint(self):
        pass

    def test_delete_association_by_service(self):
        pass

    def test_delete_association_by_region(self):
        pass

    def test_delete_association_by_policy(self):
        pass
