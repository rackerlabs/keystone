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
from keystone.contrib.endpoint_filter import controllers


class EndpointFilterExtension(wsgi.V3ExtensionRouter):
    """API Endpoints for the Endpoint Filter extension.

    The API looks like::

        GET /OS-EP-FILTER/projects/$project_id/endpoints/$endpoint_id
        HEAD /OS-EP-FILTER/projects/$project_id/endpoints/$endpoint_id
        DELETE /OS-EP-FILTER/projects/$project_id/endpoints/$endpoint_id
        GET /OS-EP-FILTER/endpoints/$endpoint_id/projects
        GET /OS-EP-FILTER/projects/$project_id/endpoints

        POST /OS-EP-FILTER/endpoint_groups
        GET /OS-EP-FILTER/endpoint_groups/$endpoint_group_id
        HEAD /OS-EP-FILTER/endpoint_groups/$endpoint_group_id
        PATCH /OS-EP-FILTER/endpoint_groups/$endpoint_group_id
        DELETE /OS-EP-FILTER/endpoint_groups/$endpoint_group_id

        GET /OS-EP-FILTER/endpoint_groups/$endpoint_group_id/projects
        GET /OS-EP-FILTER/endpoint_groups/$endpoint_group_id/endpoints

        PUT /OS-EP-FILTER/endpoint_groups/$endpoint_group/projects/$project_id
        GET /OS-EP-FILTER/endpoint_groups/$endpoint_group/projects/$project_id
        HEAD /OS-EP-FILTER/endpoint_groups/$endpoint_group/projects/$project_id
        DELETE /OS-EP-FILTER/endpoint_groups/$endpoint_group/projects/
            $project_id

    """
    PATH_PREFIX = '/OS-EP-FILTER'
    PATH_PROJECT_ENDPOINT = '/projects/{project_id}/endpoints/{endpoint_id}'
    PATH_ENDPOINT_GROUPS = '/endpoint_groups/{endpoint_group_id}'
    PATH_ENDPOINT_GROUP_PROJECTS = PATH_ENDPOINT_GROUPS + (
        '/projects/{project_id}')

    def add_routes(self, mapper):
        endpoint_filter_controller = controllers.EndpointFilterV3Controller()

        self._add_resource(
            mapper, endpoint_filter_controller,
            path=self.PATH_PREFIX + '/endpoints/{endpoint_id}/projects',
            get_action='list_projects_for_endpoint')
        self._add_resource(
            mapper, endpoint_filter_controller,
            path=self.PATH_PREFIX + self.PATH_PROJECT_ENDPOINT,
            get_head_action='check_endpoint_in_project',
            put_action='add_endpoint_to_project',
            delete_action='remove_endpoint_from_project')
        self._add_resource(
            mapper, endpoint_filter_controller,
            path=self.PATH_PREFIX + '/projects/{project_id}/endpoints',
            get_action='list_endpoints_for_project')
        self._add_resource(
            mapper, endpoint_filter_controller,
            path=self.PATH_PREFIX + '/endpoint_groups',
            post_action='create_endpoint_group')
        self._add_resource(
            mapper, endpoint_filter_controller,
            path=self.PATH_PREFIX + self.PATH_ENDPOINT_GROUPS,
            get_action='get_endpoint_group',
            head_action='check_endpoint_group',
            patch_action='update_endpoint_group',
            delete_action='remove_endpoint_group')
        self._add_resource(
            mapper, endpoint_filter_controller,
            path=self.PATH_PREFIX + self.PATH_ENDPOINT_GROUPS + (
                '/projects'),
            get_action='list_projects_associated_with_endpoint_group')
        self._add_resource(
            mapper, endpoint_filter_controller,
            path=self.PATH_PREFIX + self.PATH_ENDPOINT_GROUPS + (
                '/endpoints'),
            get_action='list_endpoints_associated_with_endpoint_group')
        self._add_resource(
            mapper, endpoint_filter_controller,
            path=self.PATH_PREFIX + self.PATH_ENDPOINT_GROUP_PROJECTS,
            get_head_action='check_endpoint_group_in_project',
            get_action='list_endpoint_groups_for_project',
            put_action='add_endpoint_group_to_project',
            delete_action='remove_endpoint_group_from_project')
