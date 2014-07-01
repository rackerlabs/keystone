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

import webob.dec

from keystone.common import wsgi
from keystone.contrib.ec2 import controllers
from keystone.openstack.common import jsonutils


class Ec2Extension(wsgi.ExtensionRouter):
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


class Ec2ExtensionV3(wsgi.ExtensionRouter):

    def add_routes(self, mapper):
        ec2_controller = controllers.Ec2ControllerV3()
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
            action='ec2_create_credential',
            conditions=dict(method=['POST']))
        mapper.connect(
            '/users/{user_id}/credentials/OS-EC2',
            controller=ec2_controller,
            action='ec2_list_credentials',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/users/{user_id}/credentials/OS-EC2/{credential_id}',
            controller=ec2_controller,
            action='ec2_get_credential',
            conditions=dict(method=['GET']))
        mapper.connect(
            '/users/{user_id}/credentials/OS-EC2/{credential_id}',
            controller=ec2_controller,
            action='ec2_delete_credential',
            conditions=dict(method=['DELETE']))

    def _get_version_data(self):
        return (
            ('http://docs.openstack.org/identity/rel/v3/ext/OS-EC2/1.0/'
             'ec2tokens',
             {
                 'href': '/ec2tokens',
             }
             ),
            ('http://docs.openstack.org/identity/rel/v3/ext/OS-EC2/1.0/'
             'user-credentials',
             {
                 'href-template': '/users/{user_id}/credentials/OS-EC2',
                 'href-vars': {
                     'user_id':
                     'http://docs.openstack.org/identity/v3/param/user_id',
                 },
             }
             ),
            ('http://docs.openstack.org/identity/rel/v3/ext/OS-EC2/1.0/'
             'user-credential',
             {
                 'href-template': '/users/{user_id}/credentials/OS-EC2/'
                 '{credential_id}',
                 'href-vars': {
                     'credential_id':
                     'http://docs.openstack.org/identity/rel/v3/ext/OS-EC2/'
                     '1.0/param/user-credential',
                     'user_id':
                     'http://docs.openstack.org/identity/v3/param/user_id',
                 },
             }
             ),
        )

    def _update_version_response(self, response_data):
        extension_version_data = self._get_version_data()
        response_data['resources'].update(extension_version_data)

    @webob.dec.wsgify()
    def __call__(self, request):
        if request.path_info != '/':
            # Not a request for version info so forward to super.
            return super(Ec2ExtensionV3, self).__call__(request)

        response = request.get_response(self.application)

        if response.status_code != 200:
            # The request failed, so don't update the response.
            return response

        if response.headers['Content-Type'] != 'application/json-home':
            # Not a request for JSON Home document, so don't update the
            # response.
            return response

        body_obj = jsonutils.loads(response.body)
        self._update_version_response(body_obj)
        response.body = jsonutils.dumps(body_obj)
        return response
