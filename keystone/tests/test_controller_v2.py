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


ADMIN_CONTEXT = {'is_admin': True}


class TenantTestCase(tests.TestCase):
    def test_get_project_users_no_user(self):
        # If a non-existant user has a role on a project, then
        # get_project_users returns a fake user.

        self.load_backends()
        self.load_fixtures(default_fixtures)
        tenant_controller = controllers.Tenant()
        role_controller = controllers.Role()

        # Add a non-existant user to the `mtu` project
        # ('mtu' has no assignments)

        project_id = self.tenant_mtu['id']

        user_id = uuid.uuid4().hex
        role_controller.add_role_to_user(
            ADMIN_CONTEXT, user_id, self.role_other['id'], project_id)

        # Should get back a fake user.

        users = tenant_controller.get_project_users(ADMIN_CONTEXT, project_id)

        exp_name = ('user-%s' % user_id)
        exp_user = {
            'id': user_id,
            'name': exp_name,
            'username': exp_name,
            'enabled': True
        }
        self.assertEqual(exp_user, users['users'][0])
