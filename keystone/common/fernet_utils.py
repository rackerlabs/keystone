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

import base64

from oslo_log import log

from keystone.common import dependency
import keystone.conf
from keystone.i18n import _LE


LOG = log.getLogger(__name__)

CONF = keystone.conf.CONF

# NOTE(lbragstad): In the event there are no encryption keys on disk, let's use
# a default one until a proper key repository is set up. This allows operators
# to gracefully upgrade from Mitaka to Newton without a key repository,
# especially in multi-node deployments. The NULL_KEY is specific to credential
# encryption only and has absolutely no beneficial purpose outside of easing
# upgrades.
NULL_KEY = base64.urlsafe_b64encode(b'\x00' * 32)


@dependency.requires('fernet_key_store_api')
class FernetUtils(object):

    def __init__(self, key_repository=None, max_active_keys=None):
        self.key_repository = key_repository
        self.max_active_keys = max_active_keys

    def validate_key_repository(self, requires_write=False):
        return self.fernet_key_store_api.validate_key_repository(
            self.key_repository,
            requires_write=requires_write)

    def create_key_directory(self, keystone_user_id=None,
                             keystone_group_id=None):
        """Attempt to create the key directory if it doesn't exist."""
        self.fernet_key_store_api.create_key_directory(self.key_repository,
                                                       keystone_user_id,
                                                       keystone_group_id)

    def _convert_to_integers(self, id_value):
        """Cast user and group system identifiers to integers."""
        # NOTE(lbragstad) os.chown() will raise a TypeError here if
        # keystone_user_id and keystone_group_id are not integers. Let's cast
        # them to integers if we can because it's possible to pass non-integer
        # values into the fernet_setup utility.
        try:
            id_int = int(id_value)
        except ValueError as e:
            msg = _LE('Unable to convert Keystone user or group ID. Error: %s')
            LOG.error(msg, e)
            raise

        return id_int

    def initialize_key_repository(self, keystone_user_id=None,
                                  keystone_group_id=None):
        """Create a key repository and bootstrap it with a key.

        :param keystone_user_id: User ID of the Keystone user.
        :param keystone_group_id: Group ID of the Keystone user.

        """
        self.fernet_key_store_api.initialize_key_repository(
            self.key_repository,
            self.max_active_keys,
            keystone_user_id,
            keystone_group_id)

    def rotate_keys(self, keystone_user_id=None, keystone_group_id=None):
        """Create a new primary key and revoke excess active keys.

        :param keystone_user_id: User ID of the Keystone user.
        :param keystone_group_id: Group ID of the Keystone user.

        Key rotation utilizes the following behaviors:

        - The highest key number is used as the primary key (used for
          encryption).
        - All keys can be used for decryption.
        - New keys are always created as key "0," which serves as a placeholder
          before promoting it to be the primary key.

        This strategy allows you to safely perform rotation on one node in a
        cluster, before syncing the results of the rotation to all other nodes
        (during both key rotation and synchronization, all nodes must recognize
        all primary keys).

        """
        self.fernet_key_store_api.rotate_keys(self.key_repository,
                                              self.max_active_keys,
                                              keystone_user_id,
                                              keystone_group_id)

    def load_keys(self, use_null_key=False):
        """Load keys from disk into a list.

        The first key in the list is the primary key used for encryption. All
        other keys are active secondary keys that can be used for decrypting
        tokens.

        :param use_null_key: If true, a known key containing null bytes will be
                             appended to the list of returned keys.

        """
        key_list = self.fernet_key_store_api.load_keys(self.key_repository,
                                                       self.max_active_keys)
        if use_null_key:
            key_list.append(NULL_KEY)

        return key_list
