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

from cryptography import fernet
from oslo_log import log

import keystone.conf
from keystone.credential.providers import core
from keystone import exception
from keystone.i18n import _
import keystone.token.providers.fernet.utils as fernet_utils


CONF = keystone.conf.CONF
LOG = log.getLogger(__name__)


class Provider(core.Provider):

    @property
    def crypto(self):
        keys = [fernet.Fernet(key) for key in self._get_encryption_keys()]
        return fernet.MultiFernet(keys)

    def __init__(self):
        self.utils = fernet_utils.CredentialUtils()

    def _get_encryption_keys(self):
        return self.utils.load_keys()

    def encrypt(self, data):
        try:
            return self.crypto.encrypt(data.encode('utf-8'))
        except (TypeError, ValueError):
            if CONF.credential.allow_plaintext:
                return data
            else:
                msg = _('Could not encrypt credentials')
                LOG.error(msg)
                raise exception.CredentialEncryptionError(msg)

    def decrypt(self, token):
        try:
            return self.crypto.decrypt(bytes(token)).decode('utf-8')
        except (fernet.InvalidToken, TypeError, ValueError):
            if CONF.credential.allow_plaintext:
                return token
            else:
                msg = _('Could not decrypt credentials')
                LOG.error(msg)
                raise exception.CredentialEncryptionError(msg)
