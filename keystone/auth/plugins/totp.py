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

import json

from oslo_log import log

from keystone import auth
from keystone.auth import plugins
from keystone.common import dependency
from keystone.common import driver_hints
from keystone.common.totp import core as totp
from keystone import exception
from keystone.i18n import _


METHOD_NAME = 'totp'

LOG = log.getLogger(__name__)


@dependency.requires('credential_api')
class TOTP(auth.AuthMethodHandler):

    def authenticate(self, context, auth_payload, auth_context):
        """Try to authenticate using TOTP"""
        user_info = plugins.TOTPUserInfo.create(auth_payload,
                                                METHOD_NAME)
        auth_passcode = auth_payload.get('user').get('passcode')
        user_id = user_info.user_id

        hints = driver_hints.Hints()
        hints.add_filter('user_id', user_id)
        hints.add_filter('type', 'totp')
        credentials = self.credential_api.list_credentials(hints=hints)

        valid_passcode = False
        for credential in credentials:
            try:
                totp_credentials = json.loads(credential['blob'])
                totp_secret = totp_credentials['secret']
                generated_passcode = totp.get_totp_token(totp_secret)
                if auth_passcode == generated_passcode:
                    valid_passcode = True
                    break
            except (ValueError, KeyError) as e:
                LOG.debug('currupt TOTP credentials with id %s',
                          credential['id'])
                pass

        if not valid_passcode:
            # authentication failed because of invalid username or passcode
            msg = _('Invalid username or passcode')
            raise exception.Unauthorized(msg)

        auth_context['user_id'] = user_info.user_id
