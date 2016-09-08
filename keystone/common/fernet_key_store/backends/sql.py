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

from keystone.common.fernet_key_store.backends import base
from keystone.common import sql
import keystone.conf
from keystone.i18n import _LI


LOG = log.getLogger(__name__)

CONF = keystone.conf.CONF


class FernetUtilsModel(sql.ModelBase, sql.DictBase):
    __tablename__ = 'fernet_keys'
    attributes = ['id', 'key']
    id = sql.Column(sql.String(64), primary_key=True)
    key = sql.Column(sql.String(44), nullable=False)

    def to_id_key_dict(self):
        return {int(self.id): self.key}


class FernetUtils(base.FernetUtilsDriver):

    def initialize_key_repository(self, *args, **kwargs):
        with sql.session_for_write() as session:
            ref = session.query(FernetUtilsModel).get('0')
            # do nothing if repository already initialized
            if ref:
                return
            key = fernet.Fernet.generate_key()
            ref = FernetUtilsModel(id='0', key=key.decode('utf-8'))
            session.add(ref)

        self.rotate_keys(*args, **kwargs)

    def rotate_keys(self, *args, **kwargs):
        with sql.session_for_write() as session:
            keys = []
            refs = session.query(FernetUtilsModel).all()
            for ref in refs:
                keys.append(ref.id)
            keys.sort(key=int, reverse=True)

            LOG.info(_LI('Starting key rotation with %(count)s keys: '
                         '%(keys)s'), {
                'count': len(keys),
                'keys': str(keys)})

            # determine the number of the new primary key
            current_primary_key = keys[0]
            LOG.info(_LI('Current primary key is: %s'), current_primary_key)
            new_primary_key = str(int(current_primary_key) + 1)
            LOG.info(_LI('Next primary key will be: %s'), new_primary_key)

            # generate new key value for 'zero' key and create new primary key
            zero_key = session.query(FernetUtilsModel).get('0')
            new_primary = FernetUtilsModel(id=new_primary_key,
                                           key=zero_key.key)
            new_zero_key = fernet.Fernet.generate_key()
            session.query(FernetUtilsModel).filter_by(id='0').\
                update({'key': new_zero_key.encode('utf-8')})
            session.add(new_primary)
            LOG.info(_LI('Promoted key 0 to be the primary: %s'),
                     new_primary_key)

            max_active_keys = args[1]
            # +1 new primary key
            old_keys_amount = len(keys) + 1 - max_active_keys
            # remove 'zero' key from local list
            keys.pop()

            # purge excess keys
            for i in range(old_keys_amount):
                session.query(FernetUtilsModel).\
                    filter_by(id=keys.pop()).delete()

    def load_keys(self, *args, **kwargs):
        with sql.session_for_read() as session:
            keys = dict()
            refs = session.query(FernetUtilsModel).all()
            for ref in refs:
                keys.update(ref.to_id_key_dict())

            max_active_keys = args[1]
            if len(keys) != max_active_keys:
                # Once the number of keys matches max_active_keys, this log
                # entry is too repetitive to be useful. Also note that it only
                # makes sense to log this message for tokens since credentials
                # doesn't have a `max_active_key` configuration option.
                LOG.debug(
                    'Loaded %(count)d Fernet keys, but '
                    '`[fernet_tokens] max_active_keys = %(max)d`; perhaps '
                    'there have not been enough key rotations to reach '
                    '`max_active_keys` yet?', {
                        'count': len(keys),
                        'max': max_active_keys})

            # return the encryption_keys, sorted by key number, descending
            return [str(keys[x]) for x in sorted(keys.keys(), reverse=True)]

    def validate_key_repository(self, *args, **kwargs):
        return True

    def create_key_directory(self, *args, **kwargs):
        pass
