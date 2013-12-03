# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

import abc

from oslo.config import cfg
import six

from keystone.openstack.common.db import api as db_api
from keystone.openstack.common import log

CONF = cfg.CONF

_BACKEND_MAPPING = {'sqlalchemy': 'keystone.contrib.kds.db.sqlalchemy.api',
                    'kvs': 'keystone.contrib.kds.db.kvs.api'}

IMPL = db_api.DBAPI(backend_mapping=_BACKEND_MAPPING)
LOG = log.getLogger(__name__)

INIT_VERSION = 0


def reset():
    global IMPL
    IMPL = db_api.DBAPI(backend_mapping=_BACKEND_MAPPING)


def get_instance():
    """Return a DB API instance."""
    return IMPL


@six.add_metaclass(abc.ABCMeta)
class Connection(object):

    def db_sync(self, version=None):
        """Migrate the database to `version` or the most recent version."""

    def db_version(self):
        """Display the current database version."""
        return INIT_VERSION

    @abc.abstractmethod
    def set_key(self, name, key, signature, group, expiration=None):
        """Set key for name.

        :param string key: The encrypted key to set.
        :param string signature: The signature of the encrypted key.
        :param bool group: True if this is a group key.
        :param datetime.datetime expiration: (optional) a date for the key to
                                             expire at.

        :returns int: The integer generation of the key that was saved.
        """

    @abc.abstractmethod
    def get_key(self, name, generation=None, group=None):
        """Get key for name.

        :param string name: Key Identifier.
        :param int generation: A specific generation of key to retrieve. If not
                               set then return the most recent.
        :param bool group: Set to return specifically a group key or host key.
                           If group is False return only a host key or if True
                           return only a group key. If unset return either.

        :returns dictionary: if found returns a dictionary containing as much
                             information about the key as is known:
                             :string name: key name
                             :bool group: True if a group key
                             :string key: the encrypted key
                             :string signature: the signature of the key
                             :int generation: the generation of this key
                             :datetime.datetime expiration: key expiry time.

                             If not found at all (eg no group entry) it returns
                             None.  A subset of the above may be returned if
                             for instance the host/group is registered but
                             there are no current keys in the database.
        """
