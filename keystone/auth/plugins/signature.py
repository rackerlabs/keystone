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
from keystone.common import dependency

METHOD_NAME = 'signature'

@dependency.requires('identity_api')
class SignatureAuthInfo(object):
    def __init__(self, auth_payload):
        self.user_id = None
        self.signature = None
        self.signature_algorithm = None
        self.credential_id = None
        self._validate_and_normalize_auth_data(auth_payload)

    def _validate_and_normalize_auth_data(self, auth_payload):
        if 'signature' not in auth_payload:
            raise exception.ValidationError(attribute='signature',
                                            target=METHOD_NAME)
        signature_info = auth_payload['signature']
        access_id = signature_info['access']
        if not access_id:
           raise exception.ValidationError(attribute='access',
                                            target=METHOD_NAME)
        signature_algorithm = signature_info['algorithm']
        signature = signature_info['signature']
        if not signature or not signature_algorithm:
            raise exception.ValidationError(attribute='signature or algorithm',
                                            target=METHOD_NAME)
        data_to_sign = signature_info['data_to_sign']
        if not data_to_sign:
            raise exception.ValidationError(attribute='data_to_sign',
                                            target=METHOD_NAME)
        project_id = signature_info.get('project_id', None)

        cred_ref = utils.lookup_credential(access_id, project_id)
        blob = utils.get_blob_from_credential(cred_ref)
        project_ref = self.identity_api.get_project(cred_ref['tenant_id'])
        user_ref = self.identity_api.get_user(cred_ref['user_id'])

        # Validate that the auth info is valid and nothing is disabled
        token.validate_auth_info(self, user_ref, project_ref)
        self.user_id = user_ref['id']
        self.signature = signature
        self.signature_algorithm = signature_algorithm
        self.credential_id = cred_ref['id']

class Signature(auth.AuthMethodHandler):

    def authenticate(self, context, auth_payload, user_context):
        """Try to authenticate against the identity backend."""
        sig_info = SignatureAuthInfo(auth_payload)

        # FIXME(gyee): identity.authenticate() can use some refactoring since
        # all we care is password matches
        try:
            self.identity_api.authenticate(
                user_id=sig_info.user_id,
                password=sig_info.password)
        except AssertionError:
            # authentication failed because of invalid username or password
            msg = _('Invalid username or password')
            raise exception.Unauthorized(msg)

        if 'user_id' not in user_context:
            user_context['user_id'] = sig_info.user_id
