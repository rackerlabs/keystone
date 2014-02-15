# Copyright 2014 IBM Corp.
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

from keystone.common import sql
from keystone import identity
from keystone.identity.mapping_backends import mapping as map


class IDMapping(sql.ModelBase, sql.ModelDictMixin):
    __tablename__ = 'id_mapping'
    public_id = sql.Column(sql.String(64), primary_key=True)
    domain_id = sql.Column(sql.String(64), sql.ForeignKey('domain.id'),
                           nullable=False)
    local_id = sql.Column(sql.String(64), nullable=False)
    # NOTE(henry-nash); Postgres requires a name to be defined for an Enum
    type = sql.Column(
        sql.Enum(map.EntityType.USER, map.EntityType.GROUP,
                 name='type'),
        nullable=False)
    # Unique constraint to ensure you can't store more than one mapping to the
    # same underlying values
    __table_args__ = (sql.UniqueConstraint('domain_id', 'local_id', 'type'),
                      {})


class Mapping(identity.MappingDriver):

    def get_public_id(self, domain_id, local_id, type):
        # NOTE(henry-nash): In this case of a regeneratable public ID (e.g.
        # sha1 hash), then rather than search for the entry using the local
        # entity values, we could create the hash and do a PK lookup.  However
        # this would only work if we hashed all the entries, even those that
        # already generate UUIDs, like SQL.  Further, this would only work
        # if the generation algorithm was immutable (i.e. it has always been
        # sha1).
        session = sql.get_session()
        query = session.query(IDMapping)
        query = query.filter_by(domain_id=domain_id)
        query = query.filter_by(local_id=local_id)
        query = query.filter_by(type=type)
        try:
            public_ref = query.one()
            public_id = public_ref.public_id
            return public_id
        except sql.NotFound:
            return None

    def create_id_mapping(self, mapping, public_id=None):
        session = sql.get_session()
        with session.begin():
            if public_id is None:
                public_id = map.generate_public_ID(mapping)
            mapping['public_id'] = public_id
            mapping_ref = IDMapping.from_dict(mapping)
            session.add(mapping_ref)
        return public_id

    def get_id_mapping(self, public_id):
        session = sql.get_session()
        mapping_ref = session.query(IDMapping).get(public_id)
        if mapping_ref:
            return mapping_ref.to_dict()

    def delete_id_mapping(self, public_id):
        session = sql.get_session()
        with session.begin():
            ref = session.query(IDMapping).get(public_id)
            if ref:
                session.delete(ref)

    def purge_mapping(self, domain_id=None):
        session = sql.get_session()
        query = session.query(IDMapping)
        if domain_id is not None:
            query = query.filter_by(domain_id=domain_id)
        query.delete()
