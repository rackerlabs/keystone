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

from keystone import auth
from keystone.auth import auth_utils
from keystone.common import controller
from keystone.common import dependency
from keystone.common import utils
from keystone import config
from keystone import exception
from keystone.openstack.common.crypto import utils as crypto_utils
from keystone.openstack.common import jsonutils
from keystone.openstack.common import log
from keystone import token


CONF = config.CONF
LOG = log.getLogger(__name__)


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
        self.algorithm = None
        self.signature = None
        self.signing_key = None
        self.data_to_sign = None

    def _validate_signature_info(self, auth_payload):
        for attribute in ('credential_id', 'signature', 'algorithm',
                          'data_to_sign'):
            if attribute not in auth_payload:
                raise exception.ValidationError(attribute=attribute,
                                                target='signature')

    def _normalize_credential_id(self, auth_payload):
        # NOTE(gyee): we support both 'credential_id' and 'access' to make
        # ec2 signature validate seamless as ec2 signature are generated with
        # access/secret. We only look for 'access' if 'credential_id' is
        # absent.
        if ('credential_id' not in auth_payload and
                'access' in auth_payload):
            access = auth_payload.pop('access')
            auth_payload['credential_id'] = utils.hash_access_key(access)

    def _validate_and_normalize_auth_data(self, auth_payload):
        self._normalize_credential_id(auth_payload)
        self._validate_signature_info(auth_payload)
        cred_ref = self.auth_utils.lookup_credential(
            auth_payload['credential_id'],
            project_id=auth_payload.get('project_id'))
        try:
            blob = jsonutils.loads(cred_ref['blob'])
        except TypeError:
            # NOTE(gyee): some old ec2 credentials may not be serialized JSON
            blob = cred_ref['blob']

        # make sure credential is allowed for signature authentication
        if cred_ref['type'] != CONF.signature.credential_type:
            msg = _("Credential type %(cred_type)s is not allowed for "
                    "signature authentication. Signature must be generated "
                    "with a %(cred_type_allowed)s credential.")
            params = {
                'cred_type': cred_ref['type'],
                'cred_type_allowed': CONF.signature.credential_type
            }
            msg = msg % params
            raise exception.Unauthorized(message=msg)

        # make sure user and project associated with the credential are valid
        project_ref = None
        if cred_ref.get('project_id'):
            project_ref = self.assignment_api.get_project(
                cred_ref['project_id'])
        user_ref = self.identity_api.get_user(cred_ref['user_id'])
        token.validate_auth_info(self, user_ref, project_ref)

        self.user_id = user_ref['id']
        self.algorithm = auth_payload['algorithm']
        if self.algorithm not in CONF.signature.supported_algorithms:
            msg = _("Signature algorithm %(algorithm)s is not supported. "
                    "Must be one of the following: %(supported_algorithms)s")
            params = {
                'algorithm': self.algorithm,
                'supported_algorithms': CONF.signature.supported_algorithms
            }
            msg = msg % params
            raise exception.Unauthorized(message=msg)
        self.signature = auth_payload['signature']
        self.data_to_sign = auth_payload['data_to_sign']
        self.signing_key = blob[CONF.signature.signing_key_attribute]


@dependency.requires('policy_api', 'token_api')
class Signature(auth.AuthMethodHandler):
    def __init__(self):
        self.auth_utils = auth_utils.AuthUtils()

    @controller.protected()
    def check_signature(self, context, sig_info, user_context):
        crypto = crypto_utils.SymmetricCrypto(
            hashtype=sig_info.algorithm)
        signature = crypto.sign(self.auth_utils.get_utf8_value(
            sig_info.signing_key), self.auth_utils.get_utf8_value(
                sig_info.data_to_sign))
        if not utils.auth_str_equal(sig_info.signature, signature):
            msg = _('Invalid signature')
            raise exception.Unauthorized(message=msg)
        if 'user_id' not in user_context:
            user_context['user_id'] = sig_info.user_id

    def authenticate(self, context, auth_payload, user_context):
        sig_info = SignatureAuthInfo.create(auth_payload)
        self.check_signature(context, sig_info, user_context)
