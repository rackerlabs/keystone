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

from keystone.common import controller
from keystone.tests import unit as tests


class ResourceV3toV2MethodsTestCase(tests.TestCase):
    """Test Resource V3 to V2 conversion methods."""
    def setUp(self):
        super(ResourceV3toV2MethodsTestCase, self).setUp()

        self.project_id = uuid.uuid4().hex
        self.domain_id = uuid.uuid4().hex
        self.parent_id = uuid.uuid4().hex
        # Project with only domain_id in ref
        self.project1 = {'id': self.project_id,
                         'name': self.project_id,
                         'domain_id': self.domain_id}
        # Project with both domain_id and parent_id in ref
        self.project2 = {'id': self.project_id,
                         'name': self.project_id,
                         'domain_id': self.domain_id,
                         'parent_id': self.parent_id}
        # Project with no domain_id and parent_id in ref
        self.project3 = {'id': self.project_id,
                         'name': self.project_id,
                         'domain_id': self.domain_id,
                         'parent_id': self.parent_id}
        # Expected result with no domain_id and parent_id
        self.expected_project = {'id': self.project_id,
                                 'name': self.project_id}

    def test_v2controller_filter_domain_id(self):
        # V2.0 is not domain aware, ensure domain_id is popped off the ref.
        other_data = uuid.uuid4().hex
        domain_id = uuid.uuid4().hex
        ref = {'domain_id': domain_id,
               'other_data': other_data}

        ref_no_domain = {'other_data': other_data}
        expected_ref = ref_no_domain.copy()

        updated_ref = controller.V2Controller.filter_domain_id(ref)
        self.assertIs(ref, updated_ref)
        self.assertDictEqual(ref, expected_ref)
        # Make sure we don't error/muck up data if domain_id isn't present
        updated_ref = controller.V2Controller.filter_domain_id(ref_no_domain)
        self.assertIs(ref_no_domain, updated_ref)
        self.assertDictEqual(ref_no_domain, expected_ref)

    def test_v3controller_filter_domain_id(self):
        # No data should be filtered out in this case.
        other_data = uuid.uuid4().hex
        domain_id = uuid.uuid4().hex
        ref = {'domain_id': domain_id,
               'other_data': other_data}

        expected_ref = ref.copy()
        updated_ref = controller.V3Controller.filter_domain_id(ref)
        self.assertIs(ref, updated_ref)
        self.assertDictEqual(ref, expected_ref)

    def test_v2controller_filter_project_parent_id(self):
        # V2.0 is not project hierarchy aware, ensure parent_id is popped off.
        other_data = uuid.uuid4().hex
        parent_id = uuid.uuid4().hex
        ref = {'parent_id': parent_id,
               'other_data': other_data}

        ref_no_parent = {'other_data': other_data}
        expected_ref = ref_no_parent.copy()

        updated_ref = controller.V2Controller.filter_project_parent_id(ref)
        self.assertIs(ref, updated_ref)
        self.assertDictEqual(ref, expected_ref)
        # Make sure we don't error/muck up data if parent_id isn't present
        updated_ref = controller.V2Controller.filter_project_parent_id(
            ref_no_parent)
        self.assertIs(ref_no_parent, updated_ref)
        self.assertDictEqual(ref_no_parent, expected_ref)

    def test_v3_to_v2_project_method(self):
        updated_project1 = controller.V2Controller.v3_to_v2_project(
            self.project1)
        self.assertIs(self.project1, updated_project1)
        self.assertDictEqual(self.project1, self.expected_project)
        updated_project2 = controller.V2Controller.v3_to_v2_project(
            self.project2)
        self.assertIs(self.project2, updated_project2)
        self.assertDictEqual(self.project2, self.expected_project)
        updated_project3 = controller.V2Controller.v3_to_v2_project(
            self.project3)
        self.assertIs(self.project3, updated_project3)
        self.assertDictEqual(self.project3, self.expected_project)

    def test_v3_to_v2_project_method_list(self):
        project_list = [self.project1, self.project2, self.project3]
        updated_list = controller.V2Controller.v3_to_v2_project(project_list)

        self.assertEqual(len(updated_list), len(project_list))

        for i, ref in enumerate(updated_list):
            # Order should not change.
            self.assertIs(ref, project_list[i])

        self.assertDictEqual(self.project1, self.expected_project)
        self.assertDictEqual(self.project2, self.expected_project)
        self.assertDictEqual(self.project3, self.expected_project)
