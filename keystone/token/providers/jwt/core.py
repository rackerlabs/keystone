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

import os

import jwt

from keystone.common import utils
import keystone.conf
from keystone.i18n import _
from keystone.token.providers import base

CONF = keystone.conf.CONF


class Provider(base.Provider):

    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)

        # NOTE(lbragstad): We add these checks here because if the jwt
        # provider is going to be used and either the `key_repository` is empty
        # or doesn't exist we should fail, hard. It doesn't make sense to start
        # keystone and just 500 because we can't do anything with an empty or
        # non-existant key repository.
        if not os.path.exists(CONF.jwt_tokens.key_repository):
            subs = {'key_repo': CONF.jwt_tokens.key_repository}
            raise SystemExit(_('%(key_repo)s does not exist') % subs)
        if not os.listdir(CONF.jwt_tokens.key_repository):
            subs = {'key_repo': CONF.jwt_tokens.key_repository}
            raise SystemExit(_('%(key_repo)s does not contain keys, use '
                               'keystone-manage jwt_setup to create '
                               'JWT keys.') % subs)

        self.token_formatter = JWTFormatter()

    def generate_id_and_issued_at(self, token):
        pass

    def validate_token(self, token_id):
        pass


class JWTFormatter(object):

    # NOTE(lbragstad): If in the future we expand support for different
    # algorithms, make this configurable and validate it against a blessed list
    # of supported algorithms.
    algorithm = 'ES256'

    def create_token(self, user_id, expires_at, audit_ids, methods,
                     system=None, domain_id=None, project_id=None,
                     trust_id=None, federated_group_ids=None,
                     identity_provider_id=None, protocol_id=None,
                     access_token_id=None, app_cred_id=None):

        issued_at = utils.isotime()
        payload = {
            'sub': user_id,
            'exp': expires_at,
            'iat': issued_at,
            'openstack_methods': methods,
            'openstack_audit_ids': audit_ids,
            'openstack_system': system,
            'openstack_domain_id': domain_id,
            'openstack_project_id': project_id,
            'openstack_trust_id': trust_id,
            'openstack_group_ids': federated_group_ids,
            'openstack_idp_id': identity_provider_id,
            'openstack_protocol_id': protocol_id,
            'openstack_access_token_id': access_token_id,
            'openstack_app_cred_id': app_cred_id
        }

        for k, v in payload.items():
            if not v:
                del payload[k]

        token_id = jwt.encode(payload, algorithm=JWTFormatter.algorithm)
        return token_id, issued_at

    def validate_token(self, token_id):
        pass
