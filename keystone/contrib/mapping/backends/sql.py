# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
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
from keystone.common.sql import migration
from keystone import exception


class LocalAttributeModel(sql.ModelBase, sql.DictBase):
    __tablename__ = 'local_attribute'
    attributes = ['id', 'rule_id', 'ks_object']

    id = sql.Column(sql.String(64), primary_key=True)
    rule_id = sql.Column(sql.String(64),
                         sql.ForeignKey('rule.id', ondelete='CASCADE'),
                         nullable=False)
    ks_object = sql.Column(sql.sql.String(64), unique=False, nullable=True)
    extra = sql.Column(sql.JsonBlob(), nullable=True)


class RemoteAttributeModel(sql.ModelBase, sql.DictBase):
    __tablename__ = 'remote_attribute'
    attributes = ['id', 'rule_id', 'type', 'requirement', 'values']

    id = sql.Column(sql.String(64), primary_key=True)
    rule_id = sql.Column(sql.String(64),
                         sql.ForeignKey('rule.id', ondelete='CASCADE'),
                         nullable=False)
    type = sql.Column(sql.String(64), unique=False, nullable=False)
    requirement = sql.Column(sql.String(64), unique=False, nullable=False)
    values = sql.Column(sql.JsonBlob(), unique=False, nullable=True)
    extra = sql.Column(sql.JsonBlob(), nullable=True)


class RuleModel(sql.ModelBase, sql.DictBase):
    __tablename__ = 'rule'
    attributes = ['id', 'mapping_id', 'extra']

    id = sql.Column(sql.String(64), primary_key=True)
    mapping_id = sql.Column(sql.String(64),
                            sql.ForeignKey('mapping.id', ondelete='CASCADE'),
                            nullable=False)
    local = sql.relationship("LocalAttributeModel",
                             foreign_keys=[LocalAttributeModel.rule_id])
    remote = sql.relationship("RemoteAttributeModel",
                              foreign_keys=[RemoteAttributeModel.rule_id])
    extra = sql.Column(sql.JsonBlob(), nullable=True)


class MappingModel(sql.ModelBase, sql.DictBase):
    __tablename__ = 'mapping'
    attributes = ['id', 'name', 'extra']

    id = sql.Column(sql.String(64), primary_key=True)
    name = sql.Column(sql.String(255), nullable=False)
    rules = sql.relationship("RuleModel", foreign_keys=[RuleModel.mapping_id])
    extra = sql.Column(sql.JsonBlob(), nullable=True)

    def to_dict(self, include_extra_dict=False):
        result = super(MappingModel,
                       self).to_dict(include_extra_dict=include_extra_dict)
        return result


class Mapping(sql.Base):

    def _get_mapping(self, session, mapping_id):
        mapping_ref = session.query(MappingModel).get(mapping_id)
        if not mapping_ref:
            raise exception.MappingNotFound(mapping_id=mapping_id)
        return mapping_ref

    def db_sync(self):
        migration.db_sync()

    def create_mapping(self, mapping):
        session = self.get_session()
        with session.begin():
            mapping_ref = MappingModel.from_dict(mapping)
            session.add(mapping_ref)
            session.flush()
        return mapping_ref.to_dict()

    def delete_mapping(self, mapping_id):
        session = self.get_session()
        with session.begin():
            mapping_ref = self._get_mapping(session, mapping_id)
            q = session.query(MappingModel)
            q = q.filter_by(id=mapping_id)
            q.delete(False)

            session.delete(mapping_ref)
            session.flush()

    def list_mappings(self):
        session = self.get_session()
        mappings = session.query(MappingModel)
        return [x.to_dict() for x in mappings]

    def get_mapping(self, mapping_id):
        session = self.get_session()
        with session.begin():
            mapping_ref = self._get_mapping(session, mapping_id)
        result = mapping_ref.to_dict()
        return result

    def update_mapping(self, mapping_id, mapping):
        session = self.get_session()
        with session.begin():
            mapping_ref = self._get_mapping(session, mapping_id)
            old_mapping = mapping_ref.to_dict()
            old_mapping.update(mapping)
            new_mapping = MappingModel.from_dict(old_mapping)
            for attr in MappingModel.attributes:
                setattr(mapping_ref, attr, getattr(new_mapping, attr))
            session.flush
        return mapping_ref.to_dict()
