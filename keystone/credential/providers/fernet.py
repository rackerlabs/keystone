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

from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken

from oslo_config import cfg
from oslo_log import log

from keystone.credential.providers import core


CONF = cfg.CONF
LOG = log.getLogger(__name__)


class Provider(core.Provider):

    def _get_encryption_keys(self):
        return CONF.credential.encryption_keys

    def _get_active_key(self):
        encryption_keys = self._get_encryption_keys()
        active_key = CONF.credential.active_key
        if len(encryption_keys) > 0 and active_key < len(encryption_keys):
            return encryption_keys[active_key]
        return None

    def encrypt(self, data):
        try:
            f = Fernet(self._get_active_key())
            return f.encrypt(data.encode('utf-8'))
        except Exception:
            if CONF.credential.allow_plaintext:
                return data

    def decrypt(self, token):
        keys = self._get_encryption_keys()

        for key in keys:
            try:
                f = Fernet(key)
                return f.decrypt(str(token)).decode('utf-8')
            except InvalidToken:
                pass

        if CONF.credential.allow_plaintext:
            return token

        raise Exception('Could not decrypt credentials')
