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
from oslo_config import cfg
from oslo_log import log

from keystone.credential.providers import core
from keystone import exception
from keystone.i18n import _


CONF = cfg.CONF
LOG = log.getLogger(__name__)


class Provider(core.Provider):

    def _get_encryption_keys(self):
        return CONF.credential.encryption_keys

    def _get_active_key(self):
        encryption_keys = self._get_encryption_keys()
        if len(encryption_keys) > 0:
            return encryption_keys[0]
        return None

    def encrypt(self, data):
        try:
            f = fernet.Fernet(self._get_active_key())
            return f.encrypt(data.encode('utf-8'))
        except (TypeError, AttributeError):
            if CONF.credential.allow_plaintext:
                return data
            else:
                msg = _('Could not encrypt credentials')
                LOG.error(msg)
                raise exception.Error(msg)

    def decrypt(self, token):
        try:
            keys = [fernet.Fernet(key) for key in self._get_encryption_keys()]
            f = fernet.MultiFernet(keys)
            return f.decrypt(bytes(token)).decode('utf-8')
        except (fernet.InvalidToken, TypeError, ValueError):
            if CONF.credential.allow_plaintext:
                return token
            else:
                msg = _('Could not decrypt credentials')
                LOG.error(msg)
                raise exception.Error(msg)
