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


from keystone import config
from keystone.tests import test_v3


CONF = config.CONF


class OpenIDTests(test_v3.RestfulTestCase):

    OIDC_AUTH_URL = 'https://localhost:8020/oidc/v10/providers/OP/authorize'
    AUTH_METHOD = 'oidc'
    AUTH_URL = '/auth/tokens'
    AUTH_REQUEST = {
        'auth': {
            'identity': {
                'methods': [
                    AUTH_METHOD
                ],
                AUTH_METHOD: {
                    'user': 'user1',
                    'password': 'security',
                    'client_id': 'rp',
                    'scope': 'openid email'
                }
            }
        }
    }

    def setUp(self):
        super(OpenIDTests, self).setUp()
        oidc_group = config.config.cfg.OptGroup(name='oidc')
        oidc_auth_opt = config.config.cfg.StrOpt('auth_url',
                                                 default=self.OIDC_AUTH_URL)
        CONF.register_opt(oidc_auth_opt, group=oidc_group)

    def test_get_token(self):
        self.post(self.AUTH_URL, body=self.AUTH_REQUEST)
