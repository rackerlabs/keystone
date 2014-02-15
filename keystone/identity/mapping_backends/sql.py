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

import uuid

from keystone.common import sql
from keystone.common.sql import migration_helpers
from keystone import identity
from keystone.openstack.common.db.sqlalchemy import migration
from keystone.openstack.common.db.sqlalchemy import session as db_session


class IDMapping(sql.ModelBase, sql.ModelDictMixin):
    __tablename__ = 'id_mapping'
    public_id = sql.Column(sql.String(64), primary_key=True)
    domain_id = sql.Column(sql.String(64), sql.ForeignKey('domain.id'),
                           nullable=False)
    local_id = sql.Column(sql.String(64), nullable=False)


class Mapping(identity.MappingDriver):

    # Internal interface to manage the database
    def db_sync(self, version=None):
        migration.db_sync(
            migration_helpers.find_migrate_repo(), version=version)

    def get_public_id(self, domain_id, local_id):
        session = db_session.get_session()
        query = session.query(IDMapping)
        query = query.filter_by(domain_id=domain_id)
        query = query.filter_by(local_id=local_id)
        try:
            public_ref = query.one()
            public_id = public_ref.public_id
            return public_id
        except sql.NotFound:
            return None

    def create_id_mapping(self, mapping, public_id=None):
        session = db_session.get_session()
        with session.begin():
            if public_id is None:
                public_id = uuid.uuid4().hex
            mapping['public_id'] = public_id
            mapping_ref = IDMapping.from_dict(mapping)
            session.add(mapping_ref)
        return public_id

    def get_id_mapping(self, public_id):
        session = db_session.get_session()
        mapping_ref = session.query(IDMapping).get(public_id)
        if mapping_ref:
            return mapping_ref.to_dict()

    def delete_id_mapping(self, public_id):
        session = db_session.get_session()
        with session.begin():
            ref = session.query(IDMapping).get(public_id)
            if ref:
                session.delete(ref)
