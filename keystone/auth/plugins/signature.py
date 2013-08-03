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
from keystone import identity
from keystone.common import controller
from keystone.common import utils
from keystone.auth.utils import AuthUtils as auth_utils
from keystone.openstack.common.crypto.utils import SymmetricCrypto

METHOD_NAME = 'signature'

class SignatureAuthInfo(object):
    def __init__(self, auth_payload):
        self.user_id = None
        self.signature_algorithm = None
        self.signature = None
        self.secret = None
        self.data_to_sign = None
        self.identity_api = identity.Manager()
        self._validate_and_normalize_auth_data(auth_payload)

    def _validate_and_normalize_auth_data(self, auth_payload):
        cred_ref, signature, signature_algorithm, data_to_sign \
            = auth_utils.lookup_credential(auth_payload)
        blob = cred_ref.get('blob')
        project_ref = self.identity_api.get_project(cred_ref['project_id'])
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
    def check_signature(self, context, sig_info, user_context):
        crypto = SymmetricCrypto(hashtype=sig_info.signature_algorithm)
        signature = crypto.sign(auth_utils.get_utf8_value(sig_info.secret),
                                auth_utils.get_utf8_value(sig_info.data_to_sign))
        if not utils.auth_str_equal(sig_info.signature, signature):
            raise exception.Unauthorized(message='Invalid EC2 signature')
        if 'user_id' not in user_context:
            user_context['user_id'] = sig_info.user_id


    def authenticate(self, context, auth_payload, user_context):
        sig_info = SignatureAuthInfo(auth_payload)
        self.check_signature(context, sig_info,user_context)


