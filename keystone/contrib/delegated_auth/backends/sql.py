# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack LLC
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
from keystone.common.sql import migration
from keystone import exception
from keystone.openstack.common import timeutils


class Consumer(sql.ModelBase, sql.DictBase):
    __tablename__ = 'consumer'
    attributes = ['id', 'name', 'consumer_key', 'consumer_secret',
                  'domain_id']
    id = sql.Column(sql.String(64), primary_key=True)
    name = sql.Column(sql.String(64))
    consumer_key = sql.Column(sql.String(64))
    consumer_secret = sql.Column(sql.String(64))
    domain_id = sql.Column(sql.String(64))
    extra = sql.Column(sql.JsonBlob())


class RequestToken(sql.ModelBase, sql.DictBase):
    __tablename__ = 'request_token'
    attributes = ['id', 'request_key', 'request_key_hash', 'request_secret',
                  'verifier', 'user_id', 'project_id', 'requested_roles',
                  'consumer_key', 'issued_at']
    id = sql.Column(sql.String(64), primary_key=True)
    request_key = sql.Column(sql.String(64))
    request_key_hash = sql.Column(sql.String(255))
    request_secret = sql.Column(sql.String(64))
    verifier = sql.Column(sql.String(64))
    user_id = sql.Column(sql.String(64))
    project_id = sql.Column(sql.String(64))
    requested_roles = sql.Column(sql.Text())
    consumer_key = sql.Column(sql.String(64))
    issued_at = sql.Column(sql.String(64))

    @classmethod
    def from_dict(cls, user_dict):
        return cls(**user_dict)

    def to_dict(self):
        return dict(self.iteritems())


class AccessToken(sql.ModelBase, sql.DictBase):
    __tablename__ = 'access_token'
    attributes = ['id', 'access_key', 'access_secret', 'user_id',
                  'project_id', 'requested_roles', 'consumer_key',
                  'issued_at']
    id = sql.Column(sql.String(64), primary_key=True)
    access_key = sql.Column(sql.String(64))
    access_secret = sql.Column(sql.String(64))
    user_id = sql.Column(sql.String(64))
    project_id = sql.Column(sql.String(64))
    requested_roles = sql.Column(sql.Text())
    consumer_key = sql.Column(sql.String(64))
    issued_at = sql.Column(sql.String(64))

    @classmethod
    def from_dict(cls, user_dict):
        return cls(**user_dict)

    def to_dict(self):
        return dict(self.iteritems())


class DelegatedAuth(sql.Base):
    def db_sync(self):
        migration.db_sync()

    def _get_consumer(self, session, consumer_id):
        consumer_ref = session.query(Consumer).get(consumer_id)
        if consumer_ref is None:
            raise exception.NotFound()
        return consumer_ref

    def get_consumer(self, consumer_id):
        session = self.get_session()
        consumer_ref = self._get_consumer(session, consumer_id)
        return consumer_ref.to_dict()

    def create_consumer(self, consumer):
        consumer_id = consumer['id']
        consumer['consumer_key'] = consumer_id
        consumer['consumer_secret'] = uuid.uuid4().hex
        session = self.get_session()
        with session.begin():
            consumer_ref = Consumer.from_dict(consumer)
            session.add(consumer_ref)
            session.flush()
        return consumer_ref.to_dict()

    def delete_consumer(self, consumer_id):
        session = self.get_session()
        with session.begin():
            ref = self._get_consumer(session, consumer_id)

            q = session.query(Consumer)
            q = q.filter_by(id=consumer_id)
            q.delete(False)

            session.delete(ref)
            session.flush()

    def list_consumers(self):
        session = self.get_session()
        consumer_refs = session.query(Consumer)
        return [x.to_dict() for x in consumer_refs]

    def update_consumer(self, consumer_id, consumer):
        session = self.get_session()
        with session.begin():
            consumer_ref = self._get_consumer(session, consumer_id)
            old_consumer_dict = consumer_ref.to_dict()
            for k in consumer:
                old_consumer_dict[k] = consumer[k]
            new_consumer = Consumer.from_dict(old_consumer_dict)
            for attr in Consumer.attributes:
                if attr != 'id':
                    setattr(consumer_ref, attr, getattr(new_consumer, attr))
            consumer_ref.extra = new_consumer.extra
            session.flush()
        return consumer_ref.to_dict()

    def create_request_token(self, consumer_key, roles, request_key_hash,
                             verifier):
        request_token = {}
        request_token_id = uuid.uuid4().hex
        request_token['request_key'] = request_token_id
        request_token['id'] = request_token_id
        request_token['request_key_hash'] = request_key_hash
        request_token['request_secret'] = uuid.uuid4().hex
        request_token['verifier'] = verifier
        request_token['user_id'] = None
        request_token['project_id'] = None
        request_token['requested_roles'] = ''.join(roles)
        request_token['consumer_key'] = consumer_key
        request_token['issued_at'] = timeutils.isotime(subsecond=True)
        session = self.get_session()
        with session.begin():
            token_ref = RequestToken.from_dict(request_token)
            session.add(token_ref)
            session.flush()
        return token_ref.to_dict()

    def _get_request_token(self, session, request_token_id):
        token_ref = session.query(RequestToken).get(request_token_id)
        if token_ref is None:
            raise exception.NotFound()
        return token_ref

    def get_request_token(self, request_token_id):
        session = self.get_session()
        token_ref = self._get_request_token(session, request_token_id)
        return token_ref.to_dict()

    def authorize_request_token(self, request_token_id, user_id, project_id):
        session = self.get_session()
        with session.begin():
            token_ref = self._get_request_token(session, request_token_id)
            token_dict = token_ref.to_dict()
            token_dict['user_id'] = user_id
            token_dict['project_id'] = project_id

            new_token = RequestToken.from_dict(token_dict)
            for attr in RequestToken.attributes:
                if attr == 'user_id' or attr == 'project_id':
                    setattr(token_ref, attr, getattr(new_token, attr))

            session.flush()
        return token_ref.to_dict()

    def create_access_token(self, user_id, project_id, consumer_key, roles):
        access_token = {}
        access_token_id = uuid.uuid4().hex
        access_token['id'] = access_token_id
        access_token['access_key'] = access_token_id
        access_token['access_secret'] = uuid.uuid4().hex
        access_token['user_id'] = user_id
        access_token['project_id'] = project_id
        access_token['requested_roles'] = roles
        access_token['consumer_key'] = consumer_key
        access_token['issued_at'] = timeutils.isotime(subsecond=True)
        session = self.get_session()
        with session.begin():
            token_ref = AccessToken.from_dict(access_token)
            session.add(token_ref)
            session.flush()
        return token_ref.to_dict()

    def _get_access_token(self, session, access_token_id):
        token_ref = session.query(AccessToken).get(access_token_id)
        if token_ref is None:
            raise exception.NotFound()
        return token_ref

    def get_access_token_for_list_authz(self, access_token_id):
        session = self.get_session()
        token_ref = self._get_access_token(session, access_token_id)
        token_dict = token_ref.to_dict()
        # formatting, delete the secret, print roles as list
        del token_dict['access_secret']
        roles = token_dict['requested_roles']
        token_dict['requested_roles'] = roles.split(',')
        return token_dict

    def list_user_authorizations(self, user_id):
        session = self.get_session()
        metadata_refs = session.query(AccessToken).filter_by(user_id=user_id)
        access_list = set([x.id for x in metadata_refs])
        return [self.get_access_token_for_list_authz(x) for x in access_list]

    def delete_user_authorization(self, user_id, access_token_id):
        session = self.get_session()
        with session.begin():
            token_ref = self._get_access_token(session, access_token_id)
            token_dict = token_ref.to_dict()
            if token_dict['user_id'] != user_id:
                raise exception.Unauthorized()

            q = session.query(Consumer)
            q = q.filter_by(id=access_token_id)
            q.delete(False)

            session.delete(token_ref)
            session.flush()
