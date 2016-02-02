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

import functools

from keystone.common import extension
from keystone.common import json_home
from keystone.common import wsgi
from keystone.compat.aws.ec2 import controllers


EXTENSION_DATA = {
    'name': 'OpenStack EC2 API',
    'namespace': 'http://docs.openstack.org/identity/api/ext/'
                 'OS-EC2/v1.0',
    'alias': 'OS-EC2',
    'updated': '2013-07-07T12:00:0-00:00',
    'description': 'OpenStack EC2 Credentials backend.',
    'links': [
        {
            'rel': 'describedby',
            'type': 'text/html',
            'href': 'http://developer.openstack.org/'
                    'api-ref-identity-v2-ext.html',
        }
    ]}
extension.register_admin_extension(EXTENSION_DATA['alias'], EXTENSION_DATA)
extension.register_public_extension(EXTENSION_DATA['alias'], EXTENSION_DATA)


build_resource_relation = functools.partial(
    json_home.build_v3_extension_resource_relation, extension_name='OS-EC2',
    extension_version='1.0')


class Ec2ExtensionV2(wsgi.RoutersBase):
    def add_routes(self, mapper):
        ec2_controller = controllers.Ec2Controller()
        # validation
        mapper.connect(
            '/ec2tokens',
            controller=ec2_controller,
            action='authenticate',
            conditions=dict(method=['POST']))

        # crud
        mapper.connect(
            '/users/{user_id}/credentials/OS-EC2',
            controller=ec2_controller,
            action='create_credential',
            conditions=dict(method=['POST']))
        mapper.connect(
            '/users/{user_id}/credentials/OS-EC2',
            controller=ec2_controller,
            action='get_credentials',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/users/{user_id}/credentials/OS-EC2/{credential_id}',
            controller=ec2_controller,
            action='get_credential',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/users/{user_id}/credentials/OS-EC2/{credential_id}',
            controller=ec2_controller,
            action='delete_credential',
            conditions=dict(method=['DELETE']))


# NOTE(morganfainberg): This is named "Routers" for V3 specific reasons, the
# code looks for a module.Routers() object
class Routers(wsgi.RoutersBase):

    def append_v3_routers(self, mapper, routers):
        ec2_controller = controllers.Ec2ControllerV3()
        # validation
        self._add_resource(
            mapper, ec2_controller,
            path='/ec2tokens',
            post_action='authenticate',
            rel=build_resource_relation(resource_name='ec2tokens'))

        # crud
        self._add_resource(
            mapper, ec2_controller,
            path='/users/{user_id}/credentials/OS-EC2',
            get_action='ec2_list_credentials',
            post_action='ec2_create_credential',
            rel=build_resource_relation(resource_name='user_credentials'),
            path_vars={
                'user_id': json_home.Parameters.USER_ID,
            })
        self._add_resource(
            mapper, ec2_controller,
            path='/users/{user_id}/credentials/OS-EC2/{credential_id}',
            get_action='ec2_get_credential',
            delete_action='ec2_delete_credential',
            rel=build_resource_relation(resource_name='user_credential'),
            path_vars={
                'credential_id':
                json_home.build_v3_parameter_relation('credential_id'),
                'user_id': json_home.Parameters.USER_ID,
            })
