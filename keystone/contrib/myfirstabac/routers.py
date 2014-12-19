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

import functools

from keystone.common import json_home
from keystone.common import wsgi
from keystone.contrib.myfirstabac import controllers


build_resource_relation = functools.partial(
    json_home.build_v3_extension_resource_relation,
    extension_name='OS-MY-FIRST-ABAC', extension_version='1.0')


class MyFirstABACExtension(wsgi.V3ExtensionRouter):

    PATH_PREFIX = '/OS-MY-FIRST-ABAC'

    def add_routes(self, mapper):
        myfirstabac_project_controller = (
            controllers.MyFirstABACProjectController())
        myfirstabac_user_controller = controllers.MyFirstABACUserController()

        self._add_resource(
            mapper, myfirstabac_project_controller,
            path=('/projects/{project_id}' + self.PATH_PREFIX +
                  '/role_if_18_or_over/{role_id}'),
            put_action='assign_role_for_18_or_over',
            rel=build_resource_relation(resource_name='myfirstabac'),
            path_vars={'project_id': json_home.Parameters.PROJECT_ID,
                       'role_id': json_home.Parameters.ROLE_ID})
        self._add_resource(
            mapper, myfirstabac_project_controller,
            path=('/projects/{project_id}' + self.PATH_PREFIX +
                  '/role_if_under_18/{role_id}'),
            put_action='assign_role_for_under_18',
            rel=build_resource_relation(resource_name='myfirstabac'),
            path_vars={'project_id': json_home.Parameters.PROJECT_ID,
                       'role_id': json_home.Parameters.ROLE_ID})
        self._add_resource(
            mapper, myfirstabac_project_controller,
            path=('/projects/{project_id}' + self.PATH_PREFIX +
                  '/role_rules'),
            get_action='get_project_role_rules',
            rel=build_resource_relation(resource_name='myfirstabac'),
            path_vars={'project_id': json_home.Parameters.PROJECT_ID})
        self._add_resource(
            mapper, myfirstabac_project_controller,
            path=('/projects/{project_id}' + self.PATH_PREFIX +
                  '/role_if_18_or_over'),
            delete_action='deassign_role_for_18_or_over',
            rel=build_resource_relation(resource_name='myfirstabac'),
            path_vars={'project_id': json_home.Parameters.PROJECT_ID})
        self._add_resource(
            mapper, myfirstabac_project_controller,
            path=('/projects/{project_id}' + self.PATH_PREFIX +
                  '/role_if_under_18'),
            delete_action='deassign_role_for_under_18',
            rel=build_resource_relation(resource_name='myfirstabac'),
            path_vars={'project_id': json_home.Parameters.PROJECT_ID})

        self._add_resource(
            mapper, myfirstabac_user_controller,
            path='/users/{user_id}' + self.PATH_PREFIX + '/age/{age}',
            put_action='add_age_attribute_to_user',
            rel=build_resource_relation(resource_name='myfirstabac'),
            path_vars={'user_id': json_home.Parameters.USER_ID,
                       'age': json_home.build_v3_parameter_relation('age')})
        self._add_resource(
            mapper, myfirstabac_user_controller,
            path='/users/{user_id}' + self.PATH_PREFIX + '/age',
            get_action='get_age_attribute_for_user',
            delete_action='remove_age_attribute_from_user',
            rel=build_resource_relation(resource_name='myfirstabac'),
            path_vars={'user_id': json_home.Parameters.USER_ID})
