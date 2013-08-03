# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack LLC
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

from keystone import auth
from keystone import exception
from keystone import token
from keystone.auth.utils import AuthUtils as utils
from keystone.common import controller
from keystone.common import dependency
from keystone.openstack.common.crypto.utils import SymmetricCrypto

METHOD_NAME = 'signature'

@dependency.requires('identity_api')
class SignatureAuthInfo(object):
    def __init__(self, auth_payload):
        self.user_id = None
        self.signature_algorithm = None
        self.signature = None
        self.secret = None
        self.data_to_sign = None
        self._validate_and_normalize_auth_data(auth_payload)

    def _validate_and_normalize_auth_data(self, auth_payload):
        if 'signature' not in auth_payload:
            raise exception.ValidationError(attribute='signature',
                                            target=METHOD_NAME)
        signature_info = auth_payload['signature']
        cred_ref, signature, signature_algorithm, data_to_sign \
            = self.lookup_credential(signature_info)
        blob = utils.get_blob_from_credential(cred_ref)
        project_ref = self.identity_api.get_project(cred_ref['tenant_id'])
        user_ref = self.identity_api.get_user(cred_ref['user_id'])

        # Validate that the auth info is valid and nothing is disabled
        token.validate_auth_info(self, user_ref, project_ref)
        self.user_id = user_ref['id']
        self.signature_algorithm = signature_algorithm
        self.signature = signature
        self.data_to_sign = data_to_sign
        self.secret = blob['secret']


class Signature(auth.AuthMethodHandler):

    @controller.protected
    def authenticate(self, context, auth_payload, user_context):
        sig_info = SignatureAuthInfo(auth_payload)
        crypto = SymmetricCrypto(hashtype=sig_info.signature_algorithm)
        signature = crypto.sign(sig_info.secret, sig_info.data_to_sign)
        if not utils.auth_str_equal(sig_info.signature, signature):
            raise exception.Unauthorized(message='Invalid EC2 signature')

        if 'user_id' not in user_context:
            user_context['user_id'] = sig_info.user_id


