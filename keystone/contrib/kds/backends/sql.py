# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Red Hat, Inc.
#
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
import copy
import hashlib
import time

from keystone.common import sql

'''
There are 2 types of keys we save here.
Individual keys and group keys.

Individual keys are identified by an id string and in 'key' is a
dictionary the contains only the base64-encoded encrypted key in a
field named 'key_v1'.
Example:
    id = d22b35312b77798eef75f195c2ed8ea78d2c26a98dedfa1c87ff0d4660636cc9
    name = 'compute.abc.example.com'
    key = {'key_v1': 'ERWERewre.....'}

Group keys use a more complex key payload, where multiple
'generations' of keys are stored with expiration times, as well as a
generation counter.
Example:
    id = a02ba163f3a02db22fdd14b310119f1a4c2f9e4a773a573f757904dd5433d4dd
    name = 'scheduler'
    key = {'generation': 10,
           'group_keys': {'9': {'key_v1': 'ERWERewre.....',
                                'expiration': 1234567890
                         },
                          '10': {'key_v1': 'GFDSAFhjhkd.....',
                                 'expiration': 1234509876
                         }
          }

'''

EXPIRATION_TIME = 600


class Keys(sql.ModelBase, sql.DictBase):
    __tablename__ = 'kds_keys'
    attributes = ['id', 'name', 'key']
    id = sql.Column(sql.String(64), primary_key=True)
    name = sql.Column(sql.Text())
    key = sql.Column(sql.JsonBlob())
    extra = sql.Column(sql.JsonBlob())


class KDS(sql.Base):

    @sql.handle_conflicts(type='kds_keys')
    def set_shared_key(self, kds_id, key):
        session = self.get_session()

        #try to remove existing entry first if any
        try:
            with session.begin():
                key_ref = session.query(Keys).filter_by(name=kds_id).first()
                session.delete(key_ref)
                session.flush()
        except Exception:
            pass

        with session.begin():
            d = dict()
            d['id'] = hashlib.sha256(kds_id).hexdigest()
            d['name'] = kds_id
            d['key'] = {'key_v1': base64.b64encode(key)}
            key_ref = Keys.from_dict(d)
            session.add(key_ref)
            session.flush()

    def set_group_key(self, kds_id, expiration=None, key=None):
        """Creates a new group of keys aor sets a new key

           If key is empty this function will create a abre entry in the
           database or fail if one exists, in this case we return 0 on
           success or an exception.
           When a key is provided the database entry is updated with the
           new key. Additionally any expired keys are removed.
           We return the generation number associated to the new key on
           success or an exception.

           :param kds_id: the name/id of the key
           :param expiration: the requested expiration time for the key
           :param key: the actual key material (will be base64 encoded
                       before being stored in the db)
           :returns: 0 when crating a new key, or the generation number
        """

        session = self.get_session()

        if key is None:
            # Create new group
            with session.begin():
                new_group = {'id': hashlib.sha256(kds_id).hexdigest(),
                             'name': kds_id,
                             'key': {'generation': 0, 'group_keys': dict()}}
                key_ref = Keys.from_dict(new_group)
                session.add(key_ref)
                session.flush()
            return 0

        key_ref = None
        cur_val = None
        new_val = None
        gen = 0
        with session.begin():
            id = hashlib.sha256(kds_id).hexdigest()
            key_ref = session.query(Keys).filter_by(id=id).first()
            cur_val = key_ref.to_dict()

            # get current entry if any, parse it and retrieve each
            # referenced generation key, then delete all the keys expired
            # by more than 10 minutes in a deepcopy
            k = cur_val['key']
            if 'generation' in k:
                gen = k['generation']
            if 'group_keys' in k:
                purge_time = time.time() - EXPIRATION_TIME
                ks = k['group_keys']
                for g in ks:
                    if ks[g]['expiration'] < purge_time:
                        if new_val is None:
                            new_val = copy.deepcopy(cur_val)
                        del new_val['key']['group_keys'][g]

            if new_val is None:
                new_val = copy.deepcopy(cur_val)

            gen = gen + 1
            bkey = base64.b64encode(key)
            new_val['key']['generation'] = gen
            new_val['key']['group_keys'][gen] = {'expiration': expiration,
                                                 'key_v1': bkey}

            # first delete old if any
            if key_ref is not None:
                session.delete(key_ref)

            # now store new generation list
            key_ref = Keys.from_dict(new_val)
            session.add(key_ref)

            session.flush()

        return gen

    def get_shared_key(self, kds_id):
        session = self.get_session()
        id = hashlib.sha256(kds_id).hexdigest()
        key_ref = session.query(Keys).filter_by(id=id).first()
        if not key_ref:
            return None
        d = key_ref.to_dict()
        return d['key']
