# Copyright 2014 IBM Corp.
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

from keystone.common import sql
from keystone.identity.mapping_backends import mapping
from keystone.tests.ksfixtures import identity_mapping as mapping_sql
from keystone.tests import test_backend_sql


class SqlIDMappingTable(test_backend_sql.SqlModels):
    """Set of tests for checking SQL Identity ID Mapping."""

    def test_id_mapping(self):
        cols = (('public_id', sql.String, 64),
                ('domain_id', sql.String, 64),
                ('local_id', sql.String, 64),
                ('type', sql.Enum, None))
        self.assertExpectedSchema('id_mapping', cols)


class SqlIDMapping(test_backend_sql.SqlTests):

    def setUp(self):
        super(SqlIDMapping, self).setUp()
        self.addCleanup(self.clean_sample_data)
        self.load_sample_data()

    def load_sample_data(self):
        domainA = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.domainA = self.assignment_api.create_domain(domainA['id'],
                                                         domainA)
        domainB = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.domainB = self.assignment_api.create_domain(domainB['id'],
                                                         domainB)

    def clean_sample_data(self):
        if self.domainA is not None:
            self.domainA['enabled'] = False
            self.assignment_api.update_domain(self.domainA['id'], self.domainA)
            self.assignment_api.delete_domain(self.domainA['id'])
        if self.domainB is not None:
            self.domainB['enabled'] = False
            self.assignment_api.update_domain(self.domainB['id'], self.domainB)
            self.assignment_api.delete_domain(self.domainB['id'])

    def test_invalid_public_key(self):
        self.assertIsNone(self.id_mapping_api.get_id_mapping(uuid.uuid4().hex))

    def test_id_mapping_crud(self):
        initial_mappings = len(mapping_sql.list_id_mappings())
        local_id1 = uuid.uuid4().hex
        local_id2 = uuid.uuid4().hex

        # Check no mappings for the new local IDs
        self.assertIsNone(self.id_mapping_api.get_public_id(
            self.domainA['id'], local_id1, mapping.EntityType.USER))
        self.assertIsNone(self.id_mapping_api.get_public_id(
            self.domainB['id'], local_id2, mapping.EntityType.GROUP))

        # Create two new mappings and the read them back
        public_id1 = self.id_mapping_api.create_id_mapping(
            {'domain_id': self.domainA['id'], 'local_id': local_id1,
             'type': mapping.EntityType.USER})
        public_id2 = self.id_mapping_api.create_id_mapping(
            {'domain_id': self.domainB['id'], 'local_id': local_id2,
             'type': mapping.EntityType.GROUP})
        self.assertEqual(initial_mappings + 2,
                         len(mapping_sql.list_id_mappings()))
        local_id_ref = self.id_mapping_api.get_id_mapping(public_id1)
        self.assertEqual(self.domainA['id'], local_id_ref['domain_id'])
        self.assertEqual(local_id1, local_id_ref['local_id'])
        self.assertEqual(mapping.EntityType.USER, local_id_ref['type'])
        # Check we have really created a new external ID
        self.assertNotEqual(local_id1, public_id1)

        local_id_ref = self.id_mapping_api.get_id_mapping(public_id2)
        self.assertEqual(self.domainB['id'], local_id_ref['domain_id'])
        self.assertEqual(local_id2, local_id_ref['local_id'])
        self.assertEqual(mapping.EntityType.GROUP, local_id_ref['type'])
        # Check we have really created a new external ID
        self.assertNotEqual(local_id2, public_id2)

        # Create another mappings, this time specifying a public ID to use
        new_public_id = uuid.uuid4().hex
        public_id3 = self.id_mapping_api.create_id_mapping(
            {'domain_id': self.domainB['id'], 'local_id': local_id2,
             'type': mapping.EntityType.USER},
            public_id=new_public_id)
        self.assertEqual(new_public_id, public_id3)
        self.assertEqual(initial_mappings + 3,
                         len(mapping_sql.list_id_mappings()))

        # Delete the mappings we created, and make sure the mapping count
        # goes back to where it was
        self.id_mapping_api.delete_id_mapping(public_id1)
        self.id_mapping_api.delete_id_mapping(public_id2)
        self.id_mapping_api.delete_id_mapping(public_id3)
        self.assertEqual(initial_mappings,
                         len(mapping_sql.list_id_mappings()))

    def test_delete_public_id_is_silent(self):
        # Test that deleting an invalid public key is silent
        self.id_mapping_api.delete_id_mapping(uuid.uuid4().hex)

    def test_purge_mapping(self):
        initial_mappings = len(mapping_sql.list_id_mappings())
        local_id1 = uuid.uuid4().hex
        local_id2 = uuid.uuid4().hex
        local_id3 = uuid.uuid4().hex

        # Create three new mappings,two in domainB, one in domainA
        public_id1 = self.id_mapping_api.create_id_mapping(
            {'domain_id': self.domainA['id'], 'local_id': local_id1,
             'type': mapping.EntityType.USER})
        self.id_mapping_api.create_id_mapping(
            {'domain_id': self.domainB['id'], 'local_id': local_id2,
             'type': mapping.EntityType.GROUP})
        self.id_mapping_api.create_id_mapping(
            {'domain_id': self.domainB['id'], 'local_id': local_id3,
             'type': mapping.EntityType.USER})

        self.assertEqual(initial_mappings + 3,
                         len(mapping_sql.list_id_mappings()))

        # Purge mappings for domainB, should be left with just one mapping
        self.id_mapping_api.purge_mapping(self.domainB['id'])
        self.assertEqual(initial_mappings + 1,
                         len(mapping_sql.list_id_mappings()))
        self.id_mapping_api.get_id_mapping(public_id1)

        # Purge mappings for domainA, should remove last one
        self.id_mapping_api.purge_mapping(self.domainA['id'])
        self.assertEqual(initial_mappings,
                         len(mapping_sql.list_id_mappings()))


class SqlIDSha1Mapping(SqlIDMapping):

    def config_overrides(self):
        super(SqlIDSha1Mapping, self).config_overrides()
        self.config_fixture.config(group='identity_mapping',
                                   public_id_generator='sha1')
