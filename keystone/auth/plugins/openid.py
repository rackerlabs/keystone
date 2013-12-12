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

import requests

from keystone import auth
from keystone import config
from keystone.openstack.common import log as logging


CONF = config.CONF
METHOD_NAME = 'openid'
LOG = logging.getLogger(__name__)


class OpenIdConnect(auth.AuthMethodHandler):

    def authenticate(self, context, auth_info, auth_context):
        """Turn a signed request with an access key into a keystone token."""
        auth_creds = ('user1', 'security')
        redirect = 'https://localhost:8021/oidcclient/redirect'
        auth_url = 'https://localhost:8020/oidc/v10/declarativeEndpoint/OAuthConfigSample/authorize'
        auth_params = {'client_id': 'rp', 'state': 'MnjaQlkOeGcSojyitJWO', 'nonce': 'af0ifjsldkj', 'response_type': 'id_token token', 'scope': 'openid', 'redirect_uri': redirect}

        r = requests.post(auth_url, params=auth_params, verify=False, auth=auth_creds)
        if r.status_code == 201:

            token_url = 'https://localhost:8020/oidc/v10/declarativeEndpoint/OAuthConfigSample/token'
            token_params = {'client_id': 'rp', 'client_secret': 'rp', 'grant_type': 'authorization_ode', 'code': 'some_code', 'redirect_uri': redirect}
            r = requests.post(token_url, params=token_params, verify=False)
            if r.status_code == 201:
                token = r.json()
                auth_context['user_id'] = token['userIdentity']
                auth_context['project_id'] = token['projectId']



        """
        # resulting token structure:
        {
            "iss": "http://ibm.com",
            "sub": "2134dsfggfs5794",
            "aud": "rp",
            "userIdentity": "user1",
            "groups": [
                {"group1", "group2"}
            ],
            "iat": 123123123,
            "exp" 123123123
            
        }
        """

