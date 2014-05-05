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

from keystone.common import config
from keystone.common import dependency
from keystone.common import wsgi
from keystone import exception
from keystone.openstack.common import log


CONF = config.CONF


def _parse_auth_data(auth):
    try:
        scheme, data = auth.split(None, 1)
    except ValueError:
        raise exception.Unauthorized()

    if scheme.lower() != 'basic':
        raise exception.Unauthorized()

    try:
        username, password = data.decode('base64').split(':', 1)
    except ValueError:
        raise exception.Unauthorized()

    domain_id = CONF.identity.default_domain_id
    return username, password, domain_id


@dependency.requires('identity_api')
class BasicAuthMiddleware(wsgi.Middleware):
    def process_request(self, request):
        authorization_header = request.headers.get('Authorization', '')
        if not authorization_header:
            return

        auth = request.environ.get('HTTP_AUTHORIZATION')
        if auth:
            user_id, password, domain_id = _parse_auth_data(auth)
            self.identity_api.authenticate(None,
                                           user_id,
                                           password)
        request.environ['REMOTE_USER'] = user_id
