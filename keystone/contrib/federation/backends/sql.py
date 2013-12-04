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
from keystone.openstack.common import jsonutils


class FederationProtocolModel(sql.ModelBase, sql.DictBase):
    __tablename__ = 'federation_protocol'
    attributes = ['id', 'idp_id', 'mapping_id']
    mutable_attributes = frozenset(['mapping_id'])

    id = sql.Column(sql.String(64), primary_key=True, autoincrement=False)
    idp_id = sql.Column(sql.String(64), sql.ForeignKey('identity_provider.id',
                        ondelete='CASCADE'), primary_key=True)
    mapping_id = sql.Column(sql.String(64), nullable=True)
    extra = sql.Column(sql.JsonBlob(), nullable=True)
    __table_args__ = (sql.UniqueConstraint('id', 'idp_id'), dict())


class IdentityProviderModel(sql.ModelBase, sql.DictBase):
    __tablename__ = 'identity_provider'
    attributes = ['id', 'name', 'enabled', 'description']
    mutable_attributes = frozenset(['description', 'name', 'enabled'])

    id = sql.Column(sql.String(64), primary_key=True)
    name = sql.Column(sql.String(255), nullable=False)
    enabled = sql.Column(sql.Boolean, nullable=False)
    description = sql.Column(sql.Text(), nullable=True)
    extra = sql.Column(sql.JsonBlob(), nullable=True)


class MappingModel(sql.ModelBase, sql.DictBase):
    __tablename__ = 'mapping'
    attributes = ['id', 'name', 'rules']

    id = sql.Column(sql.String(64), primary_key=True)
    name = sql.Column(sql.String(255), nullable=False)
    rules = sql.Column(sql.JsonBlob(), nullable=False)
    extra = sql.Column(sql.JsonBlob(), nullable=True)

    def to_dict(self, include_extra_dict=False):
        result = super(MappingModel,
                       self).to_dict(include_extra_dict=include_extra_dict)
        return result


class IdentityProvider(sql.Base):

    def db_sync(self):
        migration.db_sync()

    def create_idp(self, idp):
        session = self.get_session()
        with session.begin():
            idp_ref = IdentityProviderModel.from_dict(idp)
            session.add(idp_ref)
        return idp_ref.to_dict()

    def delete_idp(self, idp_id):
        session = self.get_session()
        with session.begin():
            idp_ref = self._get_idp(session, idp_id)
            q = session.query(IdentityProviderModel)
            q = q.filter_by(id=idp_id)
            q.delete(False)

            session.delete(idp_ref)

    def _get_idp(self, session, idp_id):
        idp_ref = session.query(IdentityProviderModel).get(idp_id)
        if not idp_ref:
            raise exception.IdentityProviderNotFound(idp_id=idp_id)
        return idp_ref

    def list_idps(self):
        session = self.get_session()
        with session.begin():
            idps = session.query(IdentityProviderModel)
        idps_list = [idp.to_dict() for idp in idps]
        return idps_list

    def get_idp(self, idp_id):
        session = self.get_session()
        idp_ref = self._get_idp(session, idp_id)
        return idp_ref.to_dict()

    def update_idp(self, idp_id, identity_provider):
        session = self.get_session()
        with session.begin():
            idp_ref = self._get_idp(session, idp_id)
            old_idp = idp_ref.to_dict()
            old_idp.update(identity_provider)
            new_idp = IdentityProviderModel.from_dict(old_idp)
            for attr in IdentityProviderModel.mutable_attributes:
                setattr(idp_ref, attr, getattr(new_idp, attr))
        return idp_ref.to_dict()

    # Protocol management

    def _get_protocol(self, session, idp_id, protocol_id):
        q = session.query(FederationProtocolModel)
        q = q.filter_by(id=protocol_id, idp_id=idp_id)
        try:
            return q.one()
        except sql.NotFound:
            kwargs = {'idp_id': idp_id}
            raise exception.FederatedProtocolNotFound(**kwargs)

    def _store_protocol(self, session, protocol_ref):
        try:
            session.add(protocol_ref)
        except sql.IntegrityError:
            raise exception.ValidationError()

    @sql.handle_conflicts(conflict_type='federation_protocol')
    def put_protocol(self, idp_id, protocol_id, protocol):
        session = self.get_session()
        with session.begin():
                self._get_idp(session, idp_id)
                protocol['id'] = protocol_id
                protocol['idp_id'] = idp_id
                protocol_ref = FederationProtocolModel.from_dict(protocol)
                session.add(protocol_ref)
        return protocol_ref.to_dict()

    def update_protocol(self, idp_id, protocol_id, protocol):
        session = self.get_session()
        with session.begin():
            proto_ref = self._get_protocol(session, idp_id, protocol_id)
            old_proto = proto_ref.to_dict()
            old_proto.update(protocol)
            new_proto = FederationProtocolModel.from_dict(old_proto)
            for attr in FederationProtocolModel.mutable_attributes:
                setattr(proto_ref, attr, getattr(new_proto, attr))
        return proto_ref.to_dict()

    def get_protocol(self, idp_id, protocol_id):
        session = self.get_session()
        protocol_ref = self._get_protocol(session, idp_id, protocol_id)
        return protocol_ref.to_dict()

    def list_protocols(self, idp_id):
        session = self.get_session()
        q = session.query(FederationProtocolModel)
        q = q.filter_by(idp_id=idp_id)
        protocols = [protocol.to_dict() for protocol in q]
        return protocols

    def delete_protocol(self, idp_id, protocol_id):
        session = self.get_session()
        with session.begin():
            key_ref = self._get_protocol(session, idp_id, protocol_id)
            q = session.query(FederationProtocolModel)
            q = q.filter_by(id=protocol_id, idp_id=idp_id)
            q.delete(False)
            session.delete(key_ref)

    # Mapping CRUD
    def _get_mapping(self, session, mapping_id):
        mapping_ref = session.query(MappingModel).get(mapping_id)
        if not mapping_ref:
            raise exception.MappingNotFound(mapping_id=mapping_id)
        return mapping_ref

    def create_mapping(self, mapping):
        session = self.get_session()
        ref = {}
        ref['id'] = mapping.get('id')
        ref['name'] = mapping.get('name')
        ref['rules'] = jsonutils.dumps(mapping.get('rules'))
        with session.begin():
            mapping_ref = MappingModel.from_dict(ref)
            session.add(mapping_ref)
        return mapping_ref.to_dict()

    def delete_mapping(self, mapping_id):
        session = self.get_session()
        with session.begin():
            mapping_ref = self._get_mapping(session, mapping_id)
            q = session.query(MappingModel)
            q = q.filter_by(id=mapping_id)
            q.delete(False)
            session.delete(mapping_ref)

    def list_mappings(self):
        session = self.get_session()
        with session.begin():
            mappings = session.query(MappingModel)
        return [x.to_dict() for x in mappings]

    def get_mapping(self, mapping_id):
        session = self.get_session()
        with session.begin():
            mapping_ref = self._get_mapping(session, mapping_id)
        result = mapping_ref.to_dict()
        return result

    def update_mapping(self, mapping_id, mapping):
        ref = {}
        ref['id'] = mapping_id
        ref['name'] = mapping.get('name')
        ref['rules'] = jsonutils.dumps(mapping.get('rules'))
        session = self.get_session()
        with session.begin():
            mapping_ref = self._get_mapping(session, mapping_id)
            old_mapping = mapping_ref.to_dict()
            old_mapping.update(ref)
            new_mapping = MappingModel.from_dict(old_mapping)
            for attr in MappingModel.attributes:
                setattr(mapping_ref, attr, getattr(new_mapping, attr))
        return mapping_ref.to_dict()
