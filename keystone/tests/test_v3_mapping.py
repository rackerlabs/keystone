# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
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

from keystone.common.sql import migration
from keystone import config
from keystone import contrib
from keystone.openstack.common import importutils
from keystone.openstack.common import jsonutils
from keystone.tests import test_v3


CONF = config.CONF


class MappingTests(test_v3.RestfulTestCase):

    EXTENSION_NAME = 'mapping'
    EXTENSION_TO_ADD = 'mapping_extension'
    MAPPING_URL = '/OS-MAP/mappings/'

    def setup_database(self):
        super(MappingTests, self).setup_database()
        package_name = "%s.%s.migrate_repo" % (contrib.__name__,
                                               self.EXTENSION_NAME)
        package = importutils.import_module(package_name)
        self.repo_path = os.path.abspath(os.path.dirname(package.__file__))
        migration.db_version_control(version=None, repo_path=self.repo_path)
        migration.db_sync(version=None, repo_path=self.repo_path)

    def setUp(self):
        super(MappingTests, self).setUp()

    def assertValidMappingListResponse(self, resp, *args, **kwargs):
        return self.assertValidListResponse(
            resp,
            'mappings',
            self.assertValidMapping,
            keys_to_check=['name'],
            *args,
            **kwargs)

    def assertValidMappingResponse(self, resp, *args, **kwargs):
        return self.assertValidResponse(
            resp,
            'mapping',
            self.assertValidMapping,
            keys_to_check=['name'],
            *args,
            **kwargs)

    def assertValidMapping(self, entity, ref=None):
        self.assertIsNotNone(entity.get('name'))
        self.assertIsNotNone(entity.get('id'))
        self.assertIsNotNone(entity.get('rules'))
        if ref:
            self.assertEqual(entity['name'], ref['name'])
            self.assertEqual(jsonutils.loads(entity['rules']), ref['rules'])
        return entity


class MappingCRUDTests(MappingTests):

    large_mapping = {'name': 'large mapping',
                     'rules': [{'remote': [{'type': 'UserName',
                                            'requirement': 'any_value_of',
                                            'values': []}],
                                'local': {'user.name': None}},
                               {'remote': [{'type': 'orgPersonType',
                                            'requirement': 'not_any_of',
                                            'values': ['Contractor',
                                                       'Guest']}],
                                'local': {'group': 'Internal'}},
                               {'remote': [{'type': 'orgPersonType',
                                            'requirement': 'any_one_of',
                                            'values': ['Contractor',
                                                       'SubContractor']}],
                                'local': {'group': 'Contractors'}},
                               {'remote': [{'type': 'orgPersonType',
                                            'requirement': 'any_one_of',
                                            'values': ['Employee']},
                                           {'type': 'sn',
                                            'requirement': 'any_one_of',
                                            'values': ['Young']}],
                                'local': {'group': 'admin'}}]}

    small_mapping = {'name': 'small mapping',
                     'rules': [{'remote': [{'type': 'orgPersonType',
                                            'requirement': 'any_one_of',
                                            'values': ['Contractor',
                                                       'SubContractor']}],
                                'local': {'group': 'Contractors'}}]}

    def _create_default_mapping_entry(self):
        url = self.MAPPING_URL
        resp = self.post(url, body={'mapping': self.large_mapping})
        return resp

    def _get_id_from_response(self, resp):
        r = resp.result.get('mapping', None)
        return r.get('id')

    def test_mapping_create(self):
        resp = self._create_default_mapping_entry()
        self.assertValidMappingResponse(resp, self.large_mapping)

    def test_mapping_list(self):
        url = self.MAPPING_URL
        self._create_default_mapping_entry()
        resp = self.get(url)
        #self.assertValidMappingListResponse(resp, self.large_mapping)
        entities = resp.result.get('mappings')
        self.assertIsNotNone(entities)
        self.assertResponseStatus(resp, 200)
        self.assertValidListLinks(resp.result.get('links'))
        self.assertEqual(len(entities), 1)

    def test_mapping_delete(self):
        url = self.MAPPING_URL + '%(mapping_id)s'
        resp = self._create_default_mapping_entry()
        mapping_id = self._get_id_from_response(resp)
        url = url % {'mapping_id': str(mapping_id)}
        resp = self.delete(url)
        self.assertResponseStatus(resp, 204)
        self.get(url, expected_status=404)

    def test_mapping_get(self):
        url = self.MAPPING_URL + '%(mapping_id)s'
        resp = self._create_default_mapping_entry()
        mapping_id = self._get_id_from_response(resp)
        url = url % {'mapping_id': str(mapping_id)}
        resp = self.get(url)
        self.assertValidMappingResponse(resp, self.large_mapping)

    def test_mapping_update(self):
        url = self.MAPPING_URL + '%(mapping_id)s'
        resp = self._create_default_mapping_entry()
        mapping_id = self._get_id_from_response(resp)
        url = url % {'mapping_id': str(mapping_id)}
        resp = self.patch(url, body={'mapping': self.small_mapping})
        self.assertValidMappingResponse(resp, self.small_mapping)
        resp = self.get(url)
        self.assertValidMappingResponse(resp, self.small_mapping)
