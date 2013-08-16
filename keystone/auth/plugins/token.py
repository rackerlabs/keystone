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
from keystone.common import wsgi
from keystone import exception
from keystone.openstack.common import log as logging
from keystone.openstack.common import timeutils
from keystone.token import provider


METHOD_NAME = 'token'

LOG = logging.getLogger(__name__)


class Token(auth.AuthMethodHandler):
    def __init__(self):
        self.provider = provider.Manager()

    def _is_v3_token(self, token_ref):
        return 'token_data' in token_ref and 'token' in token_ref['token_data']

    def authenticate(self, context, auth_payload, user_context):
        try:
            if 'id' not in auth_payload:
                raise exception.ValidationError(attribute='id',
                                                target=METHOD_NAME)
            token_id = auth_payload['id']
            response = self.provider.validate_token(token_id, version=None)

            token_ref = response.get('token', response.get('access'))

            if 'OS-TRUST:trust' in token_ref:
                raise exception.Forbidden()
            if 'trust' in token_ref:
                raise exception.Forbidden()
            if 'trust_id' in token_ref.get('metadata', {}):
                raise exception.Forbidden()
            if 'OS-OAUTH1' in token_ref:
                raise exception.Forbidden()

            wsgi.validate_token_bind(context, token_ref)

            expires_at = token_ref.get('expires_at')
            if not expires_at:
                expires_at = token_ref.get('expires')
            if not expires_at:
                expires_at = timeutils.normalize_time(
                    timeutils.parse_isotime(token_ref['token']['expires']))

            # to support Grizzly-3 to Grizzly-RC1 transition
            user_context.setdefault('expires_at', expires_at)
            user_context.setdefault('user_id', token_ref['user']['id'])
            user_context['extras'].update(token_ref.get('extras', {}))
            user_context['method_names'].extend(token_ref.get('methods', []))

        except AssertionError as e:
            LOG.error(e)
            raise exception.Unauthorized(e)
