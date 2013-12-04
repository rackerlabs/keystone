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


## SQL MODELS

class IdentityProviderKeyModel(sql.ModelBase, sql.DictBase):
    __tablename__ = 'identity_provider_key'
    attributes = ['id', 'idp_id', 'key', 'extra']
    public_attributes = ['id', 'key']
    id = sql.Column(sql.String(64), primary_key=True)
    idp_id = sql.Column(sql.String(64), sql.ForeignKey('identity_provider.id',
                        ondelete='CASCADE'))
    key = sql.Column(sql.Text(), unique=False, nullable=False)
    extra = sql.Column(sql.JsonBlob(), nullable=True)

    mutable_attributes = frozenset(['key'])


class FederationProtocolModel(sql.ModelBase, sql.DictBase):
    __tablename__ = 'federation_protocol'
    attributes = ['id', 'idp_id', 'mapping_id', 'extra']
    id = sql.Column(sql.String(64), primary_key=True, autoincrement=False)
    idp_id = sql.Column(sql.String(64), sql.ForeignKey('identity_provider.id',
                        ondelete='CASCADE'), primary_key=True)
    mapping_id = sql.Column(sql.String(64), nullable=True)
    extra = sql.Column(sql.JsonBlob(), nullable=True)
    __table_args__ = (sql.UniqueConstraint('id', 'idp_id'), {})

    mutable_attributes = frozenset(['mapping_id'])


class IdentityProviderModel(sql.ModelBase, sql.DictBase):
    __tablename__ = 'identity_provider'
    attributes = ['id', 'name', 'enabled', 'domain_id',
                  'description', 'extra']

    id = sql.Column(sql.String(64), primary_key=True)
    name = sql.Column(sql.String(255), nullable=False)
    enabled = sql.Column(sql.Boolean, nullable=False)
    domain_id = sql.Column(sql.String(64), sql.ForeignKey('domain.id'),
                           nullable=False)
    description = sql.Column(sql.Text(), nullable=True)
    protocols = sql.relationship("FederationProtocolModel",
                                 foreign_keys=[FederationProtocolModel.idp_id])
    public_keys = sql.relationship("IdentityProviderKeyModel",
                                   foreign_keys=
                                   [IdentityProviderKeyModel.idp_id])
    extra = sql.Column(sql.JsonBlob(), nullable=True)

    def to_dict(self, include_extra_dict=False):
        result = super(IdentityProviderModel,
                       self).to_dict(include_extra_dict=include_extra_dict)
        result['protocols'] = [protocol.id for protocol in self.protocols]
        result['public_keys'] = [key.id for key in self.public_keys]
        return result

    mutable_attributes = frozenset(['description', 'name',
                                    'enabled'])


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

#NOTE(marek-denis): Shall we paginate it here, somehow?
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

## Public keys management

    def _get_idp_key(self, session, idp_id, key_id):
        q = session.query(IdentityProviderKeyModel)
        q = q.filter_by(id=key_id, idp_id=idp_id)
        key_ref = None
        try:
            key_ref = q.one()
        except sql.NotFound:
            kwargs = {'idp_id': idp_id}
            raise exception.IdentityProviderKeyNotFound(**kwargs)
        else:
            return key_ref

    def get_idp_key(self, idp_id, key_id):
        session = self.get_session()
        with session.begin():
            self._get_idp(session, idp_id)
            idp_key = self._get_idp_key(session, idp_id, key_id)
        return idp_key.to_dict()

    def put_idp_key(self, idp_id, key):
        session = self.get_session()
        with session.begin():
            self._get_idp(session, idp_id)
            key['idp_id'] = idp_id
            idp_key_ref = IdentityProviderKeyModel.from_dict(key)

            session.add(idp_key_ref)
        return idp_key_ref.to_dict()

    def update_idp_key(self, idp_id, key_id, public_key):
        session = self.get_session()
        with session.begin():
            key_ref = self._get_idp_key(session, idp_id, key_id)
            old_key = key_ref.to_dict()
            old_key.update(public_key)
            new_key = IdentityProviderKeyModel.from_dict(old_key)
            for attr in IdentityProviderKeyModel.mutable_attributes:
                setattr(key_ref, attr, getattr(new_key, attr))
        return key_ref.to_dict()

    def list_public_keys(self, idp_id):
        session = self.get_session()
        q = session.query(IdentityProviderKeyModel)
        q = q.filter_by(idp_id=idp_id)
        keys_list = [key.to_dict() for key in q]
        return keys_list

    def delete_idp_key(self, idp_id, key_id):
        session = self.get_session()
        with session.begin():
            key_ref = self._get_idp_key(session, idp_id, key_id)

            q = session.query(IdentityProviderKeyModel)
            q = q.filter_by(id=key_id, idp_id=idp_id)
            q.delete(False)

            session.delete(key_ref)

# Protocol management
    def _get_protocol(self, session, idp_id, protocol_id):
        q = session.query(FederationProtocolModel)
        q = q.filter_by(id=protocol_id, idp_id=idp_id)
        try:
            return q.one()
        except sql.NotFound:
            kwargs = {'idp_id': idp_id}
            raise exception.FederatedProtocolNotFound(**kwargs)

    def put_protocol(self, idp_id, protocol):
        session = self.get_session()
        with session.begin():
            self._get_idp(session, idp_id)
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
