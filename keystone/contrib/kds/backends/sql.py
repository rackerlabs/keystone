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
import time
import uuid

from keystone.common import sql

'''
There are 2 types of keys we save here.
Individual keys and group keys.

Individual keys are identified by an id string and in 'key' is a
dictionary the contains only the base64-encoded encrypted key in a
field named 'key_v1'.
Example:
    id = 123
    name = 'compute.abc.example.com'
    key = {'key_v1': 'ERWERewre.....'}

Group keys use a more complex key payload, where multiple
'generations' of keys are stored with expiration times, as well as a
generation counter.
Example:
    id = 456
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
    name = sql.Column(sql.String(256), unique=True, nullable=False, index=True)
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
            d['id'] = uuid.uuid4().hex
            d['name'] = kds_id
            d['key'] = {'key_v1': base64.b64encode(key)}
            key_ref = Keys.from_dict(d)
            session.add(key_ref)
            session.flush()

    def set_group_key(self, kds_id, expiration=None, key=None):
        session = self.get_session()

        if key is None:
            # Create new group
            with session.begin():
                n = dict()
                n['id'] = uuid.uuid4().hex
                n['name'] = kds_id
                n['key'] = {'generation': 0, 'group_keys': dict()}
                key_ref = Keys.from_dict(n)
                session.add(key_ref)
                session.flush()
            return 0

        key_ref = None
        d = None
        n = None
        gen = 0
        with session.begin():
            key_ref = session.query(Keys).filter_by(name=kds_id).first()
            d = key_ref.to_dict()

            # get current entry if any, parse it and retrieve each
            # referenced generation key, then delete all the keys expired
            # by more than 10 minutes in a deepcopy
            k = d['key']
            if 'generation' in k:
                gen = k['generation']
            if 'group_keys' in k:
                t = time.time() - EXPIRATION_TIME
                ks = k['group_keys']
                for g in ks:
                    if ks[g]['expiration'] < t:
                        if n is None:
                            n = copy.deepcopy(d)
                        del n['key']['group_keys'][g]

            if n is None:
                n = copy.deepcopy(d)

            gen = gen + 1
            n['key']['generation'] = gen
            n['key']['group_keys'][gen] = {'expiration': expiration,
                                           'key_v1': base64.b64encode(key)}

            # first delete old if any
            if key_ref is not None:
                session.delete(key_ref)

            # now store new generation list
            key_ref = Keys.from_dict(n)
            session.add(key_ref)

            session.flush()

        return gen

    def get_shared_key(self, kds_id):
        session = self.get_session()
        key_ref = session.query(Keys).filter_by(name=kds_id).first()
        if not key_ref:
            return None
        d = key_ref.to_dict()
        k = d.pop('key', None)
        return k
