# Copyright 2015 OpenStack Foundation
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

from keystone import exception
from keystone.tests import unit
from keystone.tests.unit import default_fixtures
from keystone.tests.unit.ksfixtures import database
from oslo_config import cfg


CONF = cfg.CONF


class TestAssignmentManager(unit.TestCase):

    def setUp(self):
        super(TestAssignmentManager, self).setUp()
        self.useFixture(database.Database())
        self.load_backends()
        self.load_fixtures(default_fixtures)
        self.project_id = self.tenant_bar['id']
        self.user_id = self.user_foo['id']
        self.role_id = self.role_other["id"]

    def test_add_role_to_user_and_project_greater_than_max(self):
        self.config_fixture.config(group='assignment', max_role_assignments=1)
        # foo user has role assignment from setup, so max reached
        self.assertRaises(exception.ForbiddenAction,
                          self.assignment_api.add_role_to_user_and_project,
                          user_id=self.user_id,
                          tenant_id=self.project_id,
                          role_id=self.role_id)
        roles = self.assignment_api.get_roles_for_user_and_project(
            self.user_id, self.project_id)
        self.assertFalse(self.role_id in roles)

    def test_add_role_to_user_and_project_less_than_max(self):
        self.config_fixture.config(group='assignment', max_role_assignments=50)
        roles = self.assignment_api.get_roles_for_user_and_project(
            self.user_id, self.project_id)
        self.assertFalse(self.role_id in roles)
        self.assignment_api.add_role_to_user_and_project(self.user_id,
                                                         self.project_id,
                                                         self.role_id)
        roles = self.assignment_api.get_roles_for_user_and_project(
            self.user_id, self.project_id)
        self.assertTrue(self.role_id in roles)
