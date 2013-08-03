# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

import json

from keystone import auth
from keystone.auth import auth_utils
from keystone.common import controller
from keystone.common import dependency
from keystone.common import utils
from keystone import exception
from keystone.openstack.common.crypto import utils as crypto_utils
from keystone import token


@dependency.requires('assignment_api', 'identity_api')
class SignatureAuthInfo(object):
    @staticmethod
    def create(auth_payload):
        signature_auth_info = SignatureAuthInfo()
        signature_auth_info._validate_and_normalize_auth_data(auth_payload)
        return signature_auth_info

    def __init__(self):
        self.auth_utils = auth_utils.AuthUtils()
        self.user_id = None
        self.signature_algorithm = None
        self.signature = None
        self.secret = None
        self.data_to_sign = None

    def _validate_and_normalize_auth_data(self, auth_payload):
        cred_ref = self.auth_utils.lookup_credential(auth_payload)
        blob = json.loads(cred_ref['blob'])
        project_ref = self.identity_api.get_project(cred_ref['project_id'])
        user_ref = self.identity_api.get_user(cred_ref['user_id'])

        # Validate that the auth info is valid and nothing is disabled
        token.validate_auth_info(self, user_ref, project_ref)
        self.user_id = user_ref['id']
        self.signature_algorithm = auth_payload['algorithm']
        self.signature = auth_payload['signature']
        self.data_to_sign = auth_payload['data_to_sign']
        self.secret = blob['secret']


@dependency.requires('policy_api', 'token_api')
class Signature(auth.AuthMethodHandler):
    def __init__(self):
        self.auth_utils = auth_utils.AuthUtils()

    @controller.protected()
    def check_signature(self, context, sig_info, user_context):
        crypto = crypto_utils.SymmetricCrypto(
            hashtype=sig_info.signature_algorithm)
        signature = crypto.sign(self.auth_utils.get_utf8_value(
            sig_info.secret), self.auth_utils.get_utf8_value(
                sig_info.data_to_sign))
        if not utils.auth_str_equal(sig_info.signature, signature):
            msg = _('Invalid signature')
            raise exception.Unauthorized(message=msg)
        if 'user_id' not in user_context:
            user_context['user_id'] = sig_info.user_id

    def authenticate(self, context, auth_payload, user_context):
        sig_info = SignatureAuthInfo.create(auth_payload)
        self.check_signature(context, sig_info, user_context)
