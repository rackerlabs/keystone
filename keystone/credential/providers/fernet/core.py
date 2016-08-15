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

import hashlib

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

    def _hash_fernet_key(self, fernet_key):
        key_digest = hashlib.sha1(
            fernet_key._signing_key + fernet_key._encryption_key
        ).hexdigest()
        return key_digest[:7]

    @property
    def primary_key_hash(self):
        """The first 7 bits of the primary key's hash."""
        primary_key = self.crypto._fernets[0]
        return self._hash_fernet_key(primary_key)

    @property
    def secondary_key_hashes(self):
        """List of the first 7 bits of the hash of each secondary key."""
        key_hashes = []
        for fernet_key in self.crypto._fernets:
            key_hashes.append(self._hash_fernet_key(fernet_key))
        key_hashes.remove(self.primary_key_hash)
        return key_hashes

    @property
    def crypto(self):
        keys = [fernet.Fernet(key) for key in self._get_encryption_keys()]
        return fernet.MultiFernet(keys)

    def _get_encryption_keys(self):
        self.key_utils = fernet_utils.FernetUtils(
            CONF.credential.key_repository, 3
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
            msg = _('Credential could not be decrypted. Please contact the'
                    ' administrator')
            LOG.error(msg)
            raise exception.CredentialEncryptionError(msg)
