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

from keystone.common import controller
from keystone.common import dependency


@dependency.requires('myfirstabac_api')
class MyFirstABACProjectController(controller.V3Controller):
    member_name = 'project_rules'

    @controller.protected()
    def assign_role_for_18_or_over(self, context, project_id, role_id):
        """Assign the role to be given to a user who is over 18."""
        self.myfirstabac_api.assign_role_for_18_or_over(project_id, role_id)

    @controller.protected()
    def assign_role_for_under_18(self, context, project_id, role_id):
        """Assign the role to be given to a user who is under 18."""
        self.myfirstabac_api.assign_role_for_under_18(project_id, role_id)

    @controller.protected()
    def get_project_role_rules(self, context, project_id):
        """Get the role rules for a project."""
        role_under, role_over = (
            self.myfirstabac_api.get_project_role_rules(project_id))
        ref = {'under_18': role_under, '18_and_over': role_over}
        ref.setdefault('links', {})
        path = '/projects/%(project_id)s/OS-MY-FIRST-ABAC/role_rules' % {
            'project_id': project_id}
        ref['links']['self'] = MyFirstABACUserController.base_url(
            context, path)
        return {'project_role_rules': ref}

    @controller.protected()
    def deassign_role_for_18_or_over(self, context, project_id):
        """Deassign the role to be given to a user who is over 18."""
        self.myfirstabac_api.deassign_role_for_18_or_over(project_id)

    @controller.protected()
    def deassign_role_for_under_18(self, context, project_id):
        """Deassign the role to be given to a user who is under 18."""
        self.myfirstabac_api.deassign_role_for_under_18(project_id)


@dependency.requires('myfirstabac_api')
class MyFirstABACUserController(controller.V3Controller):

    @controller.protected()
    def add_age_attribute_to_user(self, context, user_id, age):
        """Add an age to a user."""
        self.myfirstabac_api.add_age_attribute_to_user(user_id, age)

    @controller.protected()
    def get_age_attribute_for_user(self, context, user_id):
        """Get the age of a user."""
        ref = {'age': self.myfirstabac_api.get_age_attribute_for_user(user_id)}
        ref.setdefault('links', {})
        path = '/users/%(user_id)s/OS-MY-FIRST-ABAC/age' % {
            'user_id': user_id}
        ref['links']['self'] = MyFirstABACUserController.base_url(
            context, path)
        return {'user_attributes': ref}

    @controller.protected()
    def remove_age_attribute_from_user(self, context, user_id):
        """Remove an age from a user."""
        self.myfirstabac_api.remove_age_attribute_from_user(user_id)
