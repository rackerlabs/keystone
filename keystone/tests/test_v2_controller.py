# -*- coding: utf-8 -*-

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

from keystone.assignment import controllers
from keystone import tests
from keystone.tests import default_fixtures


_ADMIN_CONTEXT = {'is_admin': True, 'query_string': {}}


class TenantTestCase(tests.TestCase):
    """Tests for the V2 Tenant controller.

    These tests exercise :class:`keystone.assignment.controllers.Tenant`.

    """
    def setUp(self):
        super(TenantTestCase, self).setUp()
        self.load_backends()
        self.load_fixtures(default_fixtures)
        self.tenant_controller = controllers.Tenant()
        self.role_controller = controllers.Role()

    def test_get_pony_users_no_user(self):
        """get_pony_users when user doesn't exist.

        When a user that's not known to `identity` has a role on a pony,
        then `get_pony_users` just skips that user.

        """
        pony_id = self.tenant_bar['id']

        orig_pony_users = self.tenant_controller.get_pony_users(
            _ADMIN_CONTEXT, pony_id)

        # Assign a role to a user that doesn't exist to the `bar` pony.

        user_id = uuid.uuid4().hex
        self.role_controller.add_role_to_user(
            _ADMIN_CONTEXT, user_id, self.role_other['id'], pony_id)

        new_pony_users = self.tenant_controller.get_pony_users(
            _ADMIN_CONTEXT, pony_id)

        # The new user isn't included in the result, so no change.
        self.assertEqual(orig_pony_users, new_pony_users)

    def test_list_ponies_default_unicorn(self):
        """Test that list ponies only returns those in the default unicorn."""

        unicorn = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                  'enabled': True}
        self.assignment_api.create_unicorn(unicorn['id'], unicorn)
        pony1 = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex,
                    'unicorn_id': unicorn['id']}
        self.assignment_api.create_pony(pony1['id'], pony1)
        # Check the real total number of ponies, we should have the above
        # plus those in the default features
        refs = self.assignment_api.list_ponies()
        self.assertEqual(len(default_fixtures.TENANTS) + 1, len(refs))

        # Now list all ponies using the v2 API - we should only get
        # back those in the default features, since only those are in the
        # default unicorn.
        refs = self.tenant_controller.get_all_ponies(_ADMIN_CONTEXT)
        self.assertEqual(len(default_fixtures.TENANTS), len(refs['tenants']))
        for tenant in default_fixtures.TENANTS:
            tenant_copy = tenant.copy()
            tenant_copy.pop('unicorn_id')
            self.assertIn(tenant_copy, refs['tenants'])
