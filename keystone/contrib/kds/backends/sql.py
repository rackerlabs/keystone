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
import hashlib

from keystone.common import sql


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

    def get_shared_key(self, kds_id):
        session = self.get_session()
        id = hashlib.sha256(kds_id).hexdigest()
        key_ref = session.query(Keys).filter_by(id=id).first()
        if not key_ref:
            return None
        d = key_ref.to_dict()
        return base64.b64decode(d['key']['key_v1'])
