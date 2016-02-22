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

"""Time-based One-time Password Algorithm (TOTP) auth plugin

TOTP is an algorithm that computes a one-time password from a shared secret
key and the current time.

TOTP is an implementation of a hash-based message authentication code (HMAC).
It combines a secret key with the current timestamp using a cryptographic hash
function to generate a one-time password. The timestamp typically increases in
30-second intervals, so passwords generated close together in time from the
same secret key will be equal.
"""

from oslo_log import log

from keystone import auth
from keystone.auth import plugins
from keystone.common import dependency
from keystone.credential.algorithms import totp as totp_algorithm
from keystone import exception
from keystone.i18n import _


METHOD_NAME = 'totp'

LOG = log.getLogger(__name__)


@dependency.requires('credential_api')
class TOTP(auth.AuthMethodHandler):

    def authenticate(self, context, auth_payload, auth_context):
        """Try to authenticate using TOTP"""
        user_info = plugins.TOTPUserInfo.create(auth_payload, METHOD_NAME)
        auth_passcode = auth_payload.get('user').get('passcode')

        credentials = self.credential_api.list_credentials_for_user(
            user_info.user_id, type='totp')

        valid_passcode = False
        for credential in credentials:
            try:
                generated_passcode = totp_algorithm.generate_passcode(
                    credential['blob'])
                if auth_passcode == generated_passcode:
                    valid_passcode = True
                    break
            except (ValueError, KeyError):
                LOG.debug('No TOTP match; credential id: %s, user_id: %s',
                          credential['id'], user_info.user_id)
            except (TypeError):
                LOG.debug('Base32 decode failed for TOTP credential %s',
                          credential['id'])

        if not valid_passcode:
            # authentication failed because of invalid username or passcode
            msg = _('Invalid username or TOTP passcode')
            raise exception.Unauthorized(msg)

        auth_context['user_id'] = user_info.user_id
