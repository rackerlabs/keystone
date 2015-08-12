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


class DriverBypasser(object):

    def create_policy_association(self, policy_id=None, endpoint_id=None,
                                  service_id=None, region_id=None):
        with sql.transaction() as session:
            association = PolicyAssociation(id=uuid.uuid4().hex,
                                            policy_id=policy_id,
                                            endpoint_id=endpoint_id,
                                            service_id=service_id,
                                            region_id=region_id)
            session.add(association)

    def get_policy_association(self, policy_id=None, endpoint_id=None,
                               service_id=None, region_id=None):
        with sql.transaction() as session:
            query = session.query(PolicyAssociation)
            query = query.filter_by(policy_id=policy_id,
                                    endpoint_id=endpoint_id,
                                    service_id=service_id,
                                    region_id=region_id)
            return query.one().to_dict()

    def list_policy_association(self, policy_id=None, endpoint_id=None,
                                service_id=None, region_id=None):
        with sql.transaction() as session:
            query = session.query(PolicyAssociation)
            if policy_id:
                query = query.filter_by(policy_id=policy_id)
            if endpoint_id:
                query = query.filter_by(endpoint_id=endpoint_id)
            if service_id:
                query = query.filter_by(service_id=service_id)
            if region_id:
                query = query.filter_by(region_id=region_id)

            return [association.to_dict() for associoation in query.all()]

    def update_policy_association(self, policy_id=None, endpoint_id=None,
                                  service_id=None, region_id=None):
        with sql.transaction() as session:
            query = session.query(PolicyAssociation)
            query = query.filter_by(policy_id=policy_id,
                                    endpoint_id=endpoint_id,
                                    service_id=service_id,
                                    region_id=region_id)

            association = query.one()
            if policy_id:
                association.policy_id = policy_id
            if endpoint_id:
                association.endpoint_id = endpoint_id
            if service_id:
                association.service_id = service_id
            if region_id:
                association.region_id = region_id

    def delete_policy_association(self, policy_id=None, endpoint_id=None,
                                  service_id=None, region_id=None):
        with sql.transaction() as session:
            query = session.query(PolicyAssociation)
            query = query.filter_by(policy_id=policy_id,
                                    endpoint_id=endpoint_id,
                                    service_id=service_id,
                                    region_id=region_id)
            query.delete()


class DriverTestCase(core_sql.BaseBackendSqlTests):
    """Test cases to validate the driver handling of the table."""

    def setUp(self):
        super(DriverTestCase, self).setUp()

        self.driver = self.endpoint_policy_api.driver
        self.bypasser = DriverBypasser()

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
            self.bypasser.get_policy_association(**association)

    def test_create_duplicate_policy_association(self):
        for target in self._list_target_combinations():
            association = {'policy_id': uuid.uuid4().hex}
            association.update(target)

            self.driver.create_policy_association(**association)
            self.bypasser.get_policy_association(**association)

            new_association = association.copy()
            new_association.update({'policy_id': uuid.uuid4().hex})

            self.driver.create_policy_association(**new_association)
            self.bypasser.get_policy_association(**new_association)

            self.assertRaises(sql.NotFound,
                              self.bypasser.get_policy_association,
                              **association)

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
