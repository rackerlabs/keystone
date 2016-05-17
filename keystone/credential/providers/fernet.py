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

from oslo_config import cfg
from oslo_log import log

from keystone.credential.providers import core


CONF = cfg.CONF
LOG = log.getLogger(__name__)


class Provider(core.Provider):

    def _get_encryption_key(self):
        return CONF.credential.encryption_key

    def _get_decryption_key(self):
        return CONF.credential.decryption_key

    def encrypt(self, data):
        f = Fernet(self._get_encryption_key())
        return f.encrypt(data.encode('utf-8'))

    def decrypt(self, token):
        keys = [self._get_encryption_key()] + self._get_decryption_key()

        for key in keys:
            try:
                f = Fernet(key)
                return f.decrypt(str(token)).decode('utf-8')
            except Exception:
                pass

        if CONF.credential.allow_plaintext:
            return token

        raise Exception('Could not decrypt credentials')
