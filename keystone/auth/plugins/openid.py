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
        client_id = auth_info['client_id']
        client_secret = auth_info['client_secret']
        payload = {'id': client_id, 'secret': client_secret}

        r = requests.post(CONF.openid.token_endpoint, data=payload)
        if r.status_code == 201:
            r = requests.post(CONF.openid.authorization_endpoint)
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

