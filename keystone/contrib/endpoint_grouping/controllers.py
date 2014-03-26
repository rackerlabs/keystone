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


from keystone import assignment
from keystone.catalog import controllers as catalog_controllers
from keystone.common import controller
from keystone.common import dependency


@dependency.requires('assignment_api', 'catalog_api', 'endpoint_grouping_api')
class EndpointGroupingV3Controller(controller.V3Controller):

    @controller.protected()
    def create_endpoint_group(self, context):
        """Creates and Endpoint Group with the associated filters."""
        

    @controller.protected()
    def get_endpoint_group(self, context, endpoint_group_id):
        """Retrieve the endpoint group associated with the id if exists."""
        

    @controller.protected()
    def update_endpoint_group(self, context, endpoint_group_id):
        """Update fixed values or extend the filters."""
        

    @controller.protected()
    def remove_endpoint_group(self, context, endpoint_group_id):
        """Remove the endpoint group."""

     
    @controller.protected()
    def add_endpoint_group_to_project(self, context, project_id, endpoint_group_id):
        """Establishes an association between an endpoint group and a project."""
        

    @controller.protected()
    def check_endpoint_group_in_project(self, context, project_id, endpoint_group_id):
        """Verifies endpoint group is currently associated with given project."""
        

    @controller.protected()
    def list_endpoint_groups_for_project(self, context, project_id):
        """Lists all endpoint groups currently associated with a given project."""
        

    @controller.protected()
    def remove_endpoint_groups_from_project(self, context, project_id, endpoint_group_id):
        """Remove the endpoint groups from the association with given project."""


    @controller.protected()
    def grant_endpoint_group_in_project_to_user(self, context, project_id, endpoint_group_id, user_id):
        """Establishes a grant between an endpoint group in a project and a user."""
        

    @controller.protected()
    def check_endpoint_group_in_project_to_user(self, context, project_id, endpoint_group_id, user_id):
        """Verifies endpoint group is currently associated with given project."""
        

    @controller.protected()
    def list_endpoint_groups_in_project_granted_to_user(self, context, project_id, user_id):
        """Lists all endpoint groups currently associated with a given project."""
        

    @controller.protected()
    def remove_endpoint_group_in_project_to_user(self, context, project_id, endpoint_group_id, user_id):
        """Remove the endpoint groups from the association with given project."""


    @controller.protected()
    def list_endpoint_groups(self, context):
        """List all the endpoint groups."""


    @controller.protected()
    def list_projects_for_endpoint_group(self, context, endpoint_group_id):
        """List all the projects assigned to a specific endpoint group."""


    @controller.protected()
    def list_endpoints_for_endpoint_group(self, context, endpoint_group_id):
        """List all the endpoints filtered by a specific endpoint group."""

