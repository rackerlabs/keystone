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

from keystone.auth.plugins import mapped
from keystone.common import provider_api
from keystone.tests import unit
from keystone.tests.unit import test_v3

PROVIDERS = provider_api.ProviderAPIs

class TestMapped(test_v3.RestfulTestCase):
    def setUp(self):
        super(TestMapped, self).setUp()
        self.current_roles = PROVIDERS.assignment_api.list_role_assignments(
            user_id = self.user['id'],
            project_id = self.project['id'],
            include_names = True
        )

        original_role = unit.new_role_ref()
        original_role['id'] = self.current_roles[0]['role_id']
        original_role['name'] = self.current_roles[0]['role_name']

        new_role = unit.new_role_ref()
        PROVIDERS.role_api.create_role(
            new_role['id'],
            new_role
        )

        self.existing_roles = {
            original_role['name']: original_role,
            new_role['name']: new_role
        }
        self.shadow_projects = [{
            'name': self.project['name'],
            'parent': {
                'id': uuid.uuid4().hex
            },
            'roles': [
                original_role,
                new_role
            ]
        }]

    def test_inherit_parent_project_roles(self):
        original_roles = PROVIDERS.assignment_api.list_role_assignments(
            user_id = self.user['id'],
            project_id = self.project['id'],
            include_names = True
        )

        mapped.validate_shadow_mapping(
            shadow_projects = self.shadow_projects,
            existing_roles = self.existing_roles,
            idp_domain_id = self.domain_id,
            idp_id = None
        )
        mapped.create_projects_from_mapping(
            shadow_projects = self.shadow_projects,
            idp_domain_id = self.domain_id,
            existing_roles = self.existing_roles,
            user = self.user,
            assignment_api = PROVIDERS.assignment_api,
            resource_api = PROVIDERS.resource_api
        )

        new_roles_tmp = PROVIDERS.assignment_api.list_role_assignments(
            user_id = self.user['id'],
            project_id = self.project['id'],
            include_names = True
        )
        new_roles = set(i['role_name'] for i in new_roles_tmp)

        expected_roles = set()
        for i in original_roles:
            expected_roles.add(i['role_name'])
        for i in self.shadow_projects[0]['roles']:
            expected_roles.add(i['name'])

        self.assertEqual(expected_roles, new_roles)
