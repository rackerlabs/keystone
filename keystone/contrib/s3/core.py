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
from keystoneclient.contrib.ec2.utils import Ec2Signer

"""Main entry point into the S3 Credentials service.

This service provides S3 token validation for services configured with the
s3_token middleware to authorize S3 requests.

This service uses the same credentials used by EC2. Refer to the documentation
for the EC2 module for how to generate the required credentials.
"""

import base64
import hashlib
import hmac

import six

from keystone.common import extension
from keystone.common import json_home
from keystone.common import utils
from keystone.common import wsgi
from keystone.contrib.ec2 import controllers
from keystone import exception


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
            # TODO(ayoung): needs a description
            'type': 'text/html',
            'href': 'https://github.com/openstack/identity-api',
        }
    ]}
extension.register_admin_extension(EXTENSION_DATA['alias'], EXTENSION_DATA)


class S3Extension(wsgi.V3ExtensionRouter):
    def add_routes(self, mapper):
        controller = S3Controller()
        # validation
        self._add_resource(
            mapper, controller,
            path='/s3tokens',
            post_action='authenticate',
            rel=json_home.build_v3_extension_resource_relation(
                's3tokens', '1.0', 's3tokens'))


class S3Controller(controllers.Ec2Controller):
    def check_signature(self, creds_ref, credentials):
        string_to_sign = base64.urlsafe_b64decode(str(credentials['token']))

        if string_to_sign[0:4] != b'AWS4':
            signature = self.calculate_signature_v1(string_to_sign,
                                                    creds_ref['secret'])
        else:
            signature = self.calculate_signature_v4(string_to_sign,
                                                    creds_ref['secret'])

        if not utils.auth_str_equal(credentials['signature'], signature):
            raise exception.Unauthorized('Credential signature mismatch')

    def calculate_signature_v1(self, string_to_sign, secret_key):
        key = str(secret_key).encode('utf-8')
        if six.PY2:
            b64_encode = base64.encodestring
        else:
            b64_encode = base64.encodebytes
        signed = b64_encode(hmac.new(key, string_to_sign, hashlib.sha1)
                            .digest()).decode('utf-8').strip()
        return signed

    def calculate_signature_v4(self, string_to_sign, secret_key):
        if six.PY3:
            strings = string_to_sign.decode('ascii').split('\n')
        else:
            strings = string_to_sign.split('\n')
        if len(strings) != 4 or strings[0] != 'AWS4-HMAC-SHA256':
            raise exception.Unauthorized(
                message='Invalid EC2 signature.')
        scope = strings[2].split('/')
        if len(scope) != 4 or scope[2] != 's3' or scope[3] != 'aws4_request':
            raise exception.Unauthorized(
                message='Invalid EC2 signature.')

        def sign(key, msg):
            return hmac.new(key, Ec2Signer._get_utf8_value(msg),
                            hashlib.sha256).digest()

        signed = sign(Ec2Signer._get_utf8_value(six.b("AWS4" + secret_key)),
                      scope[0])
        signed = sign(signed, scope[1])
        signed = sign(signed, scope[2])
        signed = sign(signed, 'aws4_request')

        signature = hmac.new(signed, Ec2Signer._get_utf8_value(string_to_sign),
                             hashlib.sha256).hexdigest()
        return signature
