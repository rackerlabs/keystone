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
"""WSGI Routers for the Identity service."""
from keystone.common import router
from keystone.common import wsgi
from keystone.identity import controllers


class Admin(wsgi.ComposableRouter):
    def add_routes(self, mapper):
        # User Operations
        user_controller = controllers.User()
        mapper.connect('/users/{user_id}',
                       controller=user_controller,
                       action='get_user',
                       conditions=dict(method=['GET']))


class Routers(wsgi.RoutersBase):

    def append_v3_routers(self, mapper, routers):
        user_controller = controllers.UserV3()
        routers.append(
            router.Router(user_controller,
                          'users', 'user',
                          resource_descriptions=self._v3_resources))

        self._add_resource(
            mapper, user_controller,
            'http://docs.openstack.org/identity/rel/v3/user_change_password',
            path_template='/users/{user_id}/password',
            path_vars={
                'user_id':
                'http://docs.openstack.org/identity/v3/param/user_id',
            },
            post_action='change_password')

        self._add_resource(
            mapper, user_controller,
            'http://docs.openstack.org/identity/rel/v3/group_users',
            path_template='/groups/{group_id}/users',
            path_vars={
                'group_id':
                'http://docs.openstack.org/identity/v3/param/group_id',
            },
            get_action='list_users_in_group')

        self._add_resource(
            mapper, user_controller,
            'http://docs.openstack.org/identity/rel/v3/group_user',
            path_template='/groups/{group_id}/users/{user_id}',
            path_vars={
                'group_id':
                'http://docs.openstack.org/identity/v3/param/group_id',
                'user_id':
                'http://docs.openstack.org/identity/v3/param/user_id',
            },
            put_action='add_user_to_group',
            get_head_action='check_user_in_group',
            delete_action='remove_user_from_group')

        group_controller = controllers.GroupV3()
        routers.append(
            router.Router(group_controller,
                          'groups', 'group',
                          resource_descriptions=self._v3_resources))

        self._add_resource(
            mapper, group_controller,
            'http://docs.openstack.org/identity/rel/v3/user_groups',
            path_template='/users/{user_id}/groups',
            path_vars={
                'user_id':
                'http://docs.openstack.org/identity/v3/param/user_id',
            },
            get_action='list_groups_for_user')
