# Copyright 2017 SUSE Linux Gmbh
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

from keystone.common import json_home
from keystone.common import router
from keystone.common import wsgi
from keystone.limit import controllers


class Routers(wsgi.RoutersBase):

    def append_v3_routers(self, mapper, routers):
        #routers.append(
        #    router.Router(controllers.RegisteredLimitV3(),
        #                  'registered_limits', 'registered_limit',
        #                  resource_descriptions=self.v3_resources))
        #routers.append(
        #    router.Router(controllers.LimitV3(),
        #                  'limits', 'limit',
        #                  resource_descriptions=self.v3_resources))

        self._add_resource(
            mapper, controllers.RegisteredLimitV3(),
            path='/registered-limits',
            post_action='create_registered_limits',
            put_action='update_registered_limits',
            delete_action='delete_registered_limits',
            get_head_action='list_registered_limits',
            rel=json_home.build_v3_resource_relation('registered_limits')
            )

        self._add_resource(
            mapper, controllers.LimitV3(),
            path='/limits/{project_id}',
            put_action='create_or_update_limits',
            get_head_action='list_limits',
            delete_action='delete_limits',
            rel=json_home.build_v3_resource_relation('limits'),
            path_vars={
                'project_id': json_home.Parameters.PROJECT_ID
            })
