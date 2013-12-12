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

    def authenticate(self, context, auth_info, auth_context):
        client_id = 'rp'
        implicit_response_type = 'id_token token'
        scope = 'openid email'
        user_auth = (auth_info['user'], auth_info['password'])

        redirect = 'http://localhost:5000/auth/token_redirect/'
        auth_url = 'https://localhost:8020/oidc/v10/providers/OP/authorize'
        auth_params = {'client_id': client_id,
                       'state': uuid.uuid4().hex,
                       'nonce': uuid.uuid4().hex,
                       'response_type': implicit_response_type,
                       'scope': scope,
                       'redirect_uri': redirect}

        r = requests.post(auth_url, params=auth_params, auth=user_auth,
                          verify=False, allow_redirects=True)

        # This should really be checking the the responses status code
        if r.history[0].status_code == 302:
            data = parse.parse_qs(parse.urlparse(r.url).fragment)
            id_token = data['id_token'][0]

            segments = id_token.split('.')
            if (len(segments) != 3):
                msg = _('Wrong number of segments in token: %s')
                raise Exception(msg % id_token)

            # Blatantly taken from: http://stackoverflow.com/questions/
            # 16923931/python-google-ouath-authentication-decode-and-
            # verify-id-token
            b64string = segments[1]
            b64string = b64string.encode('ascii')
            padded = b64string + '=' * (4 - len(b64string) % 4)
            padded = base64.urlsafe_b64decode(padded)
            token_data = jsonutils.loads(padded)

            auth_context['user_id'] = token_data['sub']
            # should be: token_data['groupIds']
            auth_context['project_id'] = None
