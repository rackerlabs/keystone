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

import base64
import uuid

from oslo.config import cfg
import requests
from six.moves.urllib import parse

from keystone import auth
from keystone.common import dependency
from keystone import config
from keystone.contrib import federation
from keystone.contrib.federation import utils
from keystone.openstack.common.gettextutils import _
from keystone.openstack.common import jsonutils
from keystone.openstack.common import log

oidc_opts = [
    cfg.StrOpt('auth_url',
               default='https://localhost:8020/oidc/v10/providers/OP'
               '/authorize',
               help='OpenID Connect authorization server endpoint.'),
    cfg.StrOpt('redirect_url',
               default='http://localhost:5000/v3/OS-FEDERATION/redirect',
               help='Redirect URL for replying party'),
    cfg.StrOpt('claim_group_key',
               default='groupIds',
               help='Key used to identify group section in an OpenID'
               ' Connect Claim')
]

CONF = config.CONF
CONF.register_opts(oidc_opts, 'oidc')
LOG = log.getLogger(__name__)


@dependency.requires('federation_api', 'identity_api', 'token_api')
class OpenIdConnect(auth.AuthMethodHandler):

    method = 'oidc'
    IMPLICIT_RESP_TYPE = 'id_token token'

    def authenticate(self, context, auth_payload, auth_context):
        """Authenticate federated user and return an authentication context.

        :param context: Keystone's request context
        :param auth_payload: the content of the authentication for a
                             given method
        :param auth_context: user authentication context, a dictionary
                             shared by all plugins.

        In addition to ``user_id`` in ``auth_context``, the ``oidc``
        plugin sets ``group_ids``. When handling unscoped tokens,
        ``OS-FEDERATION:identity_provider`` and ``OS-FEDERATION:protocol``
        are set as well.

        """

        if 'id' in auth_payload:
            fields = self._handle_scoped_token(auth_payload)
        else:
            fields = self._handle_unscoped_token(context, auth_payload)

        auth_context.update(fields)

    def _handle_scoped_token(self, auth_payload):
        token_ref = self.token_api.get_token(auth_payload['id'])
        utils.validate_expiration(token_ref)
        _federation = token_ref['user'][federation.FEDERATION]
        identity_provider = _federation['identity_provider']['id']
        protocol = _federation['protocol']['id']
        group_ids = [group['id'] for group in _federation['groups']]
        mapping = self.federation_api.get_mapping_from_idp_and_protocol(
            identity_provider, protocol)
        utils.validate_groups(group_ids, mapping['id'], self.identity_api)
        return {
            'user_id': token_ref['user_id'],
            'group_ids': group_ids
        }

    def _handle_unscoped_token(self, context, auth_payload):
        claims = self._perform_handshake(auth_payload)

        identity_provider = auth_payload['identity_provider']
        protocol = auth_payload['protocol']

        mapping = self.federation_api.get_mapping_from_idp_and_protocol(
            identity_provider, protocol)
        rules = jsonutils.loads(mapping['rules'])
        rule_processor = utils.RuleProcessor(rules)

        claim_key = CONF.oidc.claim_group_key
        assertion = dict()
        assertion['REMOTE_GROUP'] = ";".join(claims[claim_key])
        mapped_properties = rule_processor.process(assertion)
        utils.validate_groups(mapped_properties['group_ids'], mapping['id'],
                              self.identity_api)

        return {
            'user_id': claims['sub'],
            'group_ids': mapped_properties['group_ids'],
            federation.IDENTITY_PROVIDER: identity_provider,
            federation.PROTOCOL: protocol
        }

    def _perform_handshake(self, auth_payload):
        client_id = auth_payload['client_id']
        scope = auth_payload['scope']
        user_auth = (auth_payload['user'], auth_payload['password'])
        auth_url = CONF.oidc.auth_url

        # Create OIDC params to send to OpendID Connect Provider
        auth_params = {'client_id': client_id,
                       'scope': scope,
                       'state': uuid.uuid4().hex,
                       'nonce': uuid.uuid4().hex,
                       'response_type': self.IMPLICIT_RESP_TYPE,
                       'redirect_uri': CONF.oidc.redirect_url}

        r = requests.post(auth_url, params=auth_params, auth=user_auth,
                          verify=False, allow_redirects=True)

        if r.status_code == 204 and r.history[0].status_code == 302:
            data = parse.parse_qs(parse.urlparse(r.url).fragment)
            id_token = data['id_token'][0]
            access_token = data['access_token'][0]

            # Compare state and scope to prevent replay attacks
            if data['state'][0] != auth_params['state']:
                msg = _('State values do not match in access token: %s')
                raise Exception(msg % access_token)

            if data['scope'][0] != auth_params['scope']:
                msg = _('Scope values do not match in access token: %s')
                raise Exception(msg % access_token)

            # Get and decode the different segments, they are separated into:
            # headers, claims and signature from id_token
            segments = id_token.split('.')
            if len(segments) != 3:
                msg = _('Wrong number of segments in token: %s')
                raise Exception(msg % id_token)

            # Decode the claim using base64 decoding
            claims_b64 = segments[1].encode('ascii')
            claims_b64 = claims_b64 + '=' * (4 - len(claims_b64) % 4)
            claims_str = base64.urlsafe_b64decode(claims_b64)
            claims = jsonutils.loads(claims_str)

            nonce = claims['nonce']
            if nonce != auth_params['nonce']:
                msg = _('Nonce values do not match in access token: %s')
                raise Exception(msg % access_token)

            return claims
        else:
            msg = _('Error interacting with OpenID Connect Provider %s')
            raise Exception(msg % auth_url)
