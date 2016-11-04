# Copyright 2012 OpenStack Foundation
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

import copy
import uuid

from keystone.common import driver_hints
from keystone import exception
from keystone.tests import unit
from keystone.tests.unit import default_fixtures


class RoleTests(object):

    def test_get_role_returns_not_found(self):
        self.assertRaises(exception.RoleNotFound,
                          self.role_api.get_role,
                          uuid.uuid4().hex)

    def test_create_duplicate_role_name_fails(self):
        role_id = uuid.uuid4().hex
        role = unit.new_role_ref(id=role_id, name='fake1name')
        self.role_api.create_role(role_id, role)
        new_role_id = uuid.uuid4().hex
        role['id'] = new_role_id
        self.assertRaises(exception.Conflict,
                          self.role_api.create_role,
                          new_role_id,
                          role)

    def test_rename_duplicate_role_name_fails(self):
        role_id1 = uuid.uuid4().hex
        role_id2 = uuid.uuid4().hex
        role1 = unit.new_role_ref(id=role_id1, name='fake1name')
        role2 = unit.new_role_ref(id=role_id2, name='fake2name')
        self.role_api.create_role(role_id1, role1)
        self.role_api.create_role(role_id2, role2)
        role1['name'] = 'fake2name'
        self.assertRaises(exception.Conflict,
                          self.role_api.update_role,
                          role_id1,
                          role1)

    def test_role_crud(self):
        role = unit.new_role_ref()
        self.role_api.create_role(role['id'], role)
        role_ref = self.role_api.get_role(role['id'])
        role_ref_dict = {x: role_ref[x] for x in role_ref}
        self.assertDictEqual(role, role_ref_dict)

        role['name'] = uuid.uuid4().hex
        updated_role_ref = self.role_api.update_role(role['id'], role)
        role_ref = self.role_api.get_role(role['id'])
        role_ref_dict = {x: role_ref[x] for x in role_ref}
        self.assertDictEqual(role, role_ref_dict)
        self.assertDictEqual(role_ref_dict, updated_role_ref)

        self.role_api.delete_role(role['id'])
        self.assertRaises(exception.RoleNotFound,
                          self.role_api.get_role,
                          role['id'])

    def test_update_role_returns_not_found(self):
        role = unit.new_role_ref()
        self.assertRaises(exception.RoleNotFound,
                          self.role_api.update_role,
                          role['id'],
                          role)

    def test_list_roles(self):
        roles = self.role_api.list_roles()
        self.assertEqual(len(default_fixtures.ROLES), len(roles))
        role_ids = set(role['id'] for role in roles)
        expected_role_ids = set(role['id'] for role in default_fixtures.ROLES)
        self.assertEqual(expected_role_ids, role_ids)

    @unit.skip_if_cache_disabled('role')
    def test_cache_layer_role_crud(self):
        role = unit.new_role_ref()
        role_id = role['id']
        # Create role
        self.role_api.create_role(role_id, role)
        role_ref = self.role_api.get_role(role_id)
        updated_role_ref = copy.deepcopy(role_ref)
        updated_role_ref['name'] = uuid.uuid4().hex
        # Update role, bypassing the role api manager
        self.role_api.driver.update_role(role_id, updated_role_ref)
        # Verify get_role still returns old ref
        self.assertDictEqual(role_ref, self.role_api.get_role(role_id))
        # Invalidate Cache
        self.role_api.get_role.invalidate(self.role_api, role_id)
        # Verify get_role returns the new role_ref
        self.assertDictEqual(updated_role_ref,
                             self.role_api.get_role(role_id))
        # Update role back to original via the assignment api manager
        self.role_api.update_role(role_id, role_ref)
        # Verify get_role returns the original role ref
        self.assertDictEqual(role_ref, self.role_api.get_role(role_id))
        # Delete role bypassing the role api manager
        self.role_api.driver.delete_role(role_id)
        # Verify get_role still returns the role_ref
        self.assertDictEqual(role_ref, self.role_api.get_role(role_id))
        # Invalidate cache
        self.role_api.get_role.invalidate(self.role_api, role_id)
        # Verify RoleNotFound is now raised
        self.assertRaises(exception.RoleNotFound,
                          self.role_api.get_role,
                          role_id)
        # recreate role
        self.role_api.create_role(role_id, role)
        self.role_api.get_role(role_id)
        # delete role via the assignment api manager
        self.role_api.delete_role(role_id)
        # verity RoleNotFound is now raised
        self.assertRaises(exception.RoleNotFound,
                          self.role_api.get_role,
                          role_id)

    def test_route_crud(self):
        # Create
        service1 = uuid.uuid4().hex
        route_ref = unit.new_route_ref()
        route_ref['service'] = service1
        route_1_created = self.role_api.create_route(
            route_ref['id'], route_ref)
        self.assertEqual(route_1_created, route_ref)

        # Read: Get
        route_1 = self.role_api.get_route(route_ref['id'])
        self.assertEqual(route_1, route_ref)

        route_ref = unit.new_route_ref()
        route_ref['service'] = service1
        route_2_created = self.role_api.create_route(
            route_ref['id'], route_ref)

        service2 = uuid.uuid4().hex
        route_ref = unit.new_route_ref()
        route_ref['service'] = service2
        route_3_created = self.role_api.create_route(
            route_ref['id'], route_ref)

        # Read:  List all
        all_routes = self.role_api.list_routes()
        self.assertEqual(3, len(all_routes))

        hints = driver_hints.Hints()
        all_routes = self.role_api.list_routes(hints)
        self.assertEqual(3, len(all_routes))

        hints.add_filter('service', service1)
        service_1_routes = self.role_api.list_routes(hints)
        self.assertEqual(2, len(service_1_routes))
        self.assertIn(route_1_created, service_1_routes)
        self.assertIn(route_2_created, service_1_routes)
        self.assertNotIn(route_3_created, service_1_routes)

        hints = driver_hints.Hints()
        hints.add_filter('service', service2)
        service_2_routes = self.role_api.list_routes(hints)
        self.assertEqual(1, len(service_2_routes))
        self.assertNotIn(route_1_created, service_2_routes)
        self.assertNotIn(route_2_created, service_2_routes)
        self.assertIn(route_3_created, service_2_routes)

        # Update
        route_1_id = route_1['id']

        route_ref = unit.new_route_ref()
        route_ref['id'] = route_1_created['id']
        route_1_updated = self.role_api.update_route(
            route_1_id,
            route_ref)

        route_1_gotten = self.role_api.get_route(
            route_1_id)

        self.assertEqual(route_ref, route_1_updated)
        self.assertEqual(route_1_gotten, route_1_updated)

        # Delete
        all_routes = self.role_api.list_routes()
        self.assertEqual(3, len(all_routes))
        self.assertIn(route_1_gotten, all_routes)
        self.assertIn(route_2_created, all_routes)
        self.assertIn(route_3_created, all_routes)

        self.role_api.delete_route(route_1_id)
        all_routes = self.role_api.list_routes()
        self.assertEqual(2, len(all_routes))

        self.assertNotIn(route_1_gotten, all_routes)
        self.assertIn(route_2_created, all_routes)
        self.assertIn(route_3_created, all_routes)
