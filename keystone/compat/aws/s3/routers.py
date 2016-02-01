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

from keystone.common import extension
from keystone.common import json_home
from keystone.common import wsgi
from keystone.compat.aws.s3 import controllers


EXTENSION_DATA = {
    'name': 'OpenStack S3 API',
    'namespace': 'http://docs.openstack.org/identity/api/ext/'
                 's3tokens/v1.0',
    'alias': 's3tokens',
    'updated': '2013-07-07T12:00:0-00:00',
    'description': 'OpenStack S3 API.',
    'links': [
        {
            'rel': 'describedby',
            'type': 'text/html',
            'href': 'http://developer.openstack.org/'
                    'api-ref-identity-v2-ext.html',
        }
    ]}

extension.register_admin_extension(EXTENSION_DATA['alias'], EXTENSION_DATA)


class Routers(wsgi.RoutersBase):
    def add_routes(self, mapper):
        controller = controllers.S3Controller()
        # validation
        self._add_resource(
            mapper, controller,
            path='/s3tokens',
            post_action='authenticate',
            rel=json_home.build_v3_extension_resource_relation(
                's3tokens', '1.0', 's3tokens'))

    def append_v3_routers(self, mapper, routers):
        controller = controllers.S3Controller()
        # validation
        self._add_resource(
            mapper, controller,
            path='/s3tokens',
            post_action='authenticate',
            rel=json_home.build_v3_extension_resource_relation(
                's3tokens', '1.0', 's3tokens'))
