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

import requests
from six.moves.urllib import parse

from keystone import auth
from keystone import config
from keystone.openstack.common import jsonutils
from keystone.openstack.common import log as logging


CONF = config.CONF
METHOD_NAME = 'oidc'
LOG = logging.getLogger(__name__)


class OpenIdConnect(auth.AuthMethodHandler):

    # Constant for OIDC
    KS_REDIRECT = 'http://localhost:5000/auth/token_redirect/'
    IMPLICIT_RESP_TYPE = 'id_token token'

    def authenticate(self, context, auth_info, auth_context):
        client_id = auth_info['client_id']
        scope = auth_info['scope']
        user_auth = (auth_info['user'], auth_info['password'])
        auth_url = CONF.oidc.auth_url

        # Create OIDC params to send to OP
        auth_params = {'client_id': client_id, 'scope': scope,
                       'state': uuid.uuid4().hex, 'nonce': uuid.uuid4().hex,
                       'response_type': self.IMPLICIT_RESP_TYPE,
                       'redirect_uri': self.KS_REDIRECT}

        r = requests.post(auth_url, params=auth_params, auth=user_auth,
                          verify=False, allow_redirects=True)

        # TODO(stevemar): This should be checking the responses status code
        if r.history[0].status_code == 302:
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

            auth_context['user_id'] = claims['sub']
            auth_context['project_id'] = claims['groupIds']
            auth_context['OS-OIDC:issuer'] = claims['iss']
