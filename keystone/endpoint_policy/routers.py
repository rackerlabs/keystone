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
from keystone.endpoint_policy import controllers


build_resource_relation = functools.partial(
    json_home.build_v3_extension_resource_relation,
    extension_name='OS-ENDPOINT-POLICY', extension_version='1.0')


class Routers(wsgi.RoutersBase):

    PATH_PREFIX = '/OS-ENDPOINT-POLICY'

    _path_prefixes = ('OS-ENDPOINT-POLICY',)

    def append_v3_routers(self, mapper, routers):
        endpoint_policy_controller = controllers.EndpointPolicyV3Controller()

        self._add_resource(
            mapper, endpoint_policy_controller,
            path='/endpoints/{endpoint_id}' + self.PATH_PREFIX + '/policy',
            get_head_action='get_policy_for_endpoint',
            rel=build_resource_relation(resource_name='endpoint_policy'),
            path_vars={'endpoint_id': json_home.Parameters.ENDPOINT_ID})
