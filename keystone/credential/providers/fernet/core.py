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

from keystone.common import fernet_utils
import keystone.conf
from keystone.credential.providers import core
from keystone import exception
from keystone.i18n import _


CONF = keystone.conf.CONF
LOG = log.getLogger(__name__)


class Provider(core.Provider):

    @property
    def crypto(self):
        keys = [fernet.Fernet(key) for key in self._get_encryption_keys()]
        return fernet.MultiFernet(keys)

    def _get_encryption_keys(self):
        self.key_utils = fernet_utils.FernetUtils(
            CONF.credential.key_repository,
            CONF.credential.max_active_keys
        )
        return self.key_utils.load_keys()

    def encrypt(self, credential):
        """Attempt to encrypt a plaintext credential.

        :param credential: a plaintext representation of a credential
        :returns: an encrypted credential
        """
        try:
            return self.crypto.encrypt(credential.encode('utf-8'))
        except (TypeError, ValueError):
            if CONF.credential.allow_plaintext:
                return credential
            else:
                msg = _('Credential could not be encrypted. Please contact the'
                        ' administrator')
                LOG.error(msg)
                raise exception.CredentialEncryptionError(msg)

    def decrypt(self, credential):
        """Attempt to decrypt a credential.

        :param credential: an encrypted credential string
        :returns: a decrypted credential
        """
        try:
            return self.crypto.decrypt(bytes(credential)).decode('utf-8')
        except (fernet.InvalidToken, TypeError, ValueError):
            if CONF.credential.allow_plaintext:
                return credential
            else:
                msg = _('Credential could not be decrypted. Please contact the'
                        ' administrator')
                LOG.error(msg)
                raise exception.CredentialEncryptionError(msg)
