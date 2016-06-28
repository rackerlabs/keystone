# Copyright 2016 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import uuid

from keystone.common import dependency
from keystone.tests.functional import core as functional_core


@dependency.requires('resource_api')
class HMTPerformanceTest(functional_core.BaseTestCase):

    TREE_DEPTH = 5
    NODE_WIDTH = 5

    def setUp(self):
        project_ref = {
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex,
            'description': uuid.uuid4().hex,
            'enabled': True,
            'domain_id': None,
            'is_domain': False,
        }
        self.test_root = self.resource_api.create_project(
            project_ref['id'], project_ref)

        parents = [project_ref]
        for _ in range(self.TREE_DEPTH):
            leaves = []
            for parent in parents:
                for _ in range(self.NODE_WIDTH):
                    project_ref = {
                        'id': uuid.uuid4().hex,
                        'name': uuid.uuid4().hex,
                        'description': uuid.uuid4().hex,
                        'enabled': True,
                        'domain_id': None,
                        'is_domain': False,
                        'parent_id': parent['id']
                    }
                    leaf = self.resource_api.create_project(
                        project_ref['id'], project_ref)
                    leaves.append(leaf)
            parents = leaves

    def test_hmt(self):
        for p in self.resource_api.list_projects_in_subtree(
                self.test_root['id']):
            self.resource_api.list_projects_in_subtree(p['id'])
            self.resource_api.list_project_parents(p['id'])

    def tearDown(self):
        for p in self.resource_api.list_projects_in_subtree(
                self.test_root['id']):
            self.resource_api.delete_project(p['id'])
        self.resource_api.delete_project(self.test_root['id'])
