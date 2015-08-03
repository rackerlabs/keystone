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

from keystone.common import sql
from keystone import exception
from keystone.tests.unit.backend import core_sql


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
    """Test cases to validate the endpoint policy driver behavior."""

    def setUp(self):
        super(DriverTestCase, self).setUp()

        self.driver = self.endpoint_policy_api.driver

        self.association = {'policy_id': uuid.uuid4().hex,
                            'endpoint_id': None,
                            'service_id': uuid.uuid4().hex,
                            'region_id': uuid.uuid4().hex}

        self.driver.create_policy_association(**self.association)

    def test_recreate_policy_association(self):
        override_association = self.association.copy()
        override_association.update({'policy_id': uuid.uuid4().hex})

        self.driver.create_policy_association(**override_association)
        self.driver.check_policy_association(**override_association)

        self.assertRaises(exception.PolicyAssociationNotFound,
                          self.driver.check_policy_association,
                          **self.association)

    def test_check_policy_association(self):
        self.driver.check_policy_association(**self.association)

        wrong_targets = [{'service_id': self.association['service_id']},
                         {'region_id': self.association['region_id']}]

        for wrong_target in wrong_targets:
            association = wrong_target.copy()
            association.update({'policy_id': self.association['policy_id']})

            self.assertRaises(exception.PolicyAssociationNotFound,
                              self.driver.check_policy_association,
                              **association)

    def test_delete_policy_association(self):
        self.driver.delete_policy_association(**self.association)

        self.assertRaises(exception.PolicyAssociationNotFound,
                          self.driver.check_policy_association,
                          **self.association)

    def test_get_policy_association(self):
        target = self.association.copy()
        policy_id = target.pop('policy_id')

        association = self.driver.get_policy_association(**target)
        self.assertEqual(policy_id, association['policy_id'])

    def test_list_associations_for_policy(self):
        another_association = {'policy_id': self.association['policy_id'],
                               'endpoint_id': None,
                               'service_id': uuid.uuid4().hex,
                               'region_id': uuid.uuid4().hex}

        self.driver.create_policy_association(**another_association)

        associations = self.driver.list_associations_for_policy(
            self.association['policy_id'])

        self.assertEqual(2, len(associations))
        self.assertIn(self.association, associations)
        self.assertIn(another_association, associations)

    def test_delete_association_by_endpoint(self):
        association = {'policy_id': uuid.uuid4().hex,
                       'endpoint_id': uuid.uuid4().hex}
        self.driver.create_policy_association(**association)

        self.driver.delete_association_by_endpoint(association['endpoint_id'])

        self.driver.check_policy_association(**self.association)
        self.assertRaises(exception.PolicyAssociationNotFound,
                          self.driver.check_policy_association,
                          **association)

    def test_delete_association_by_service(self):
        service_id = uuid.uuid4().hex
        associations = [{'policy_id': uuid.uuid4().hex,
                         'service_id': service_id,
                         'region_id': uuid.uuid4().hex},
                        {'policy_id': uuid.uuid4().hex,
                         'service_id': service_id}]

        for association in associations:
            self.driver.create_policy_association(**association)

        self.driver.delete_association_by_service(service_id)

        self.driver.check_policy_association(**self.association)
        for association in associations:
            self.assertRaises(exception.PolicyAssociationNotFound,
                              self.driver.check_policy_association,
                              **association)

    def test_delete_association_by_region(self):
        region_id = uuid.uuid4().hex
        policy_id = uuid.uuid4().hex
        associations = [{'policy_id': policy_id,
                         'service_id': uuid.uuid4().hex,
                         'region_id': region_id},
                        {'policy_id': policy_id,
                         'service_id': uuid.uuid4().hex,
                         'region_id': region_id}]

        for association in associations:
            self.driver.create_policy_association(**association)

        self.driver.delete_association_by_region(region_id)

        self.driver.check_policy_association(**self.association)
        for association in associations:
            self.assertRaises(exception.PolicyAssociationNotFound,
                              self.driver.check_policy_association,
                              **association)

    def test_delete_association_by_policy(self):
        policy_id = uuid.uuid4().hex
        associations = [{'policy_id': policy_id,
                         'service_id': uuid.uuid4().hex},
                        {'policy_id': policy_id,
                         'endpoint_id': uuid.uuid4().hex}]

        for association in associations:
            self.driver.create_policy_association(**association)

        self.driver.delete_association_by_policy(policy_id)

        self.driver.check_policy_association(**self.association)
        for association in associations:
            self.assertRaises(exception.PolicyAssociationNotFound,
                              self.driver.check_policy_association,
                              **association)
