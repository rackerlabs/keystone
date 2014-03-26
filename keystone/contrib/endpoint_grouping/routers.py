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

from keystone.common import wsgi
from keystone.contrib.endpoint_grouping import controllers


class EndpointGroupingExtension(wsgi.ExtensionRouter):

    PATH_PREFIX = '/OS-EP-GROUPING'
    PATH_PROJECT = '/projects/{project_id}'
    PATH_ENDPOINT_GROUPING = '/endpoint-groups/{endpoint_group_id}'
    PATH_USERS = '/users/{user_id}'

    def add_routes(self, mapper):
        endpoint_grouping_controller = controllers.EndpointGroupingV3Controller
        # Endpoint Grouping CRUD Operations
        mapper.connect(self.PATH_PREFIX + '/endpoint-groups',
                       controller=endpoint_grouping_controller,
                       action='create_endpoint_group',
                       conditions=dict(method=['POST']))
        mapper.connect(self.PATH_PREFIX + self.PATH_ENDPOINT_GROUPING,
                       controller=endpoint_grouping_controller,
                       action='get_endpoint_group',
                       conditions=dict(method=['GET']))
        mapper.connect(self.PATH_PREFIX + self.PATH_ENDPOINT_GROUPING,
                       controller=endpoint_grouping_controller,
                       action='update_endpoint_group',
                       conditions=dict(method=['PATCH']))
        mapper.connect(self.PATH_PREFIX + self.PATH_ENDPOINT_GROUPING,
                       controller=endpoint_grouping_controller,
                       action='remove_endpoint_group',
                       conditions=dict(method=['DELETE']))
        #Create relationships between Project and Endpoint Groups CRUD Operations
        mapper.connect(self.PATH_PREFIX + self.PATH_PROJECT + self.PATH_ENDPOINT_GROUPING,
                       controller=endpoint_grouping_controller,
                       action='add_endpoint_group_to_project',
                       conditions=dict(method=['PUT']))
        mapper.connect(self.PATH_PREFIX + self.PATH_PROJECT + self.PATH_ENDPOINT_GROUPING,
                       controller=endpoint_grouping_controller,
                       action='check_endpoint_group_in_project',
                       conditions=dict(method=['HEAD']))
        mapper.connect(self.PATH_PREFIX + self.PATH_PROJECT + '/endpoint-groups',
                       controller=endpoint_grouping_controller,
                       action='list_endpoint_groups_for_project',
                       conditions=dict(method=['GET']))
        mapper.connect(self.PATH_PREFIX + self.PATH_PROJECT + self.PATH_ENDPOINT_GROUPING,
                       controller=endpoint_grouping_controller,
                       action='remove_endpoint_group_from_project',
                       conditions=dict(method=['DELETE']))
        #Create relationship between Users and Endpoint Groups CRUD Operations
        mapper.connect(self.PATH_PREFIX + self.PATH_PROJECT
                       + self.PATH_ENDPOINT_GROUPING + self.PATH_USERS,
                       controller=endpoint_grouping_controller,
                       action='grant_endpoint_group_in_project_to_user',
                       conditions=dict(method=['PUT']))
        mapper.connect(self.PATH_PREFIX + self.PATH_PROJECT
                       + self.PATH_ENDPOINT_GROUPING + self.PATH_USERS,
                       controller=endpoint_grouping_controller,
                       action='check_endpoint_group_in_project_to_user',
                       conditions=dict(method=['HEAD']))
        mapper.connect(self.PATH_PREFIX + self.PATH_PROJECT
                       + '/endpoint-groups'+ self.PATH_USERS,
                       controller=endpoint_grouping_controller,
                       action='list_endpoint_groups_in_project_to_user',
                       conditions=dict(method=['GET']))
        mapper.connect(self.PATH_PREFIX + self.PATH_PROJECT
                       + self.PATH_ENDPOINT_GROUPING + self.PATH_USERS,
                       controller=endpoint_grouping_controller,
                       action='remove_endpoint_group_in_project_to_user',
                       conditions=dict(method=['DELETE']))
        #Look-up APIs
        mapper.connect(self.PATH_PREFIX + '/endpoint-groups',
                       controller=endpoint_grouping_controller,
                       action='list_endpoint_groups',
                       conditions=dict(method=['GET']))
        mapper.connect(self.PATH_PREFIX + self.PATH_ENDPOINT_GROUPING + '/projects',
                       controller=endpoint_grouping_controller,
                       action='list_projects_for_endpoint_group',
                       conditions=dict(method=['GET']))
        mapper.connect(self.PATH_PREFIX + self.PATH_ENDPOINT_GROUPING + '/endpoints',
                       controller=endpoint_grouping_controller,
                       action='list_endpoints_for_endpoint_group',
                       conditions=dict(method=['GET']))
        
