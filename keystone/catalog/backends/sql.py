# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2012 OpenStack LLC
# Copyright 2012 Canonical Ltd.
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

import sqlalchemy.exc
import webob.exc

from keystone.common import sql
from keystone import exception
from keystone import catalog
from keystone.common.sql import migration


class Service(sql.ModelBase, sql.DictBase):
    __tablename__ = 'service'
    id = sql.Column(sql.String(64), primary_key=True)
    name = sql.Column(sql.String(255), unique=True)
    type = sql.Column(sql.String(255))
    description = sql.Column(sql.String(255))

    @classmethod
    def from_dict(cls, service_ref):
        return cls(**service_ref)

    def to_dict(self):
        return dict(self.iteritems())


class Endpoint(sql.ModelBase, sql.DictBase):
    __tablename__ = 'endpoint'
    id = sql.Column(sql.String(64), primary_key=True)
    region = sql.Column('region', sql.String(255))
    publicurl = sql.Column(sql.String(2000))
    adminurl = sql.Column(sql.String(2000))
    internalurl = sql.Column(sql.String(2000))

    @classmethod
    def from_dict(cls, endpoint_ref):
        return cls(**endpoint_ref)

    def to_dict(self):
        return dict(self.iteritems())


class ServiceEndpointAssociation(sql.ModelBase, sql.DictBase):
    __tablename__ = "service_endpoint_association"
    service_id = sql.Column(sql.String(64),
                            sql.ForeignKey('service.id'),
                            primary_key=True)
    endpoint_id = sql.Column(sql.String(64),
                             sql.ForeignKey('endpoint.id'),
                             primary_key=True)

    @classmethod
    def from_dict(cls, assoc_ref):
        return cls(**assoc_ref)

    def to_dict(self):
        return dict(self.iteritems())


class Catalog(sql.Base):
    def db_sync(self):
        migration.db_sync()

    # Services
    def list_services(self):
        session = self.get_session()
        _services = session.query(Service)
        return list(_services)

    def get_service(self, service_ref):
        return service_ref.to_dict()

    def get_service_by_id(self, service_id):
        session = self.get_session()
        service_ref = session.query(Service).filter_by(id=service_id).first()
        return self.get_service(service_ref)

    def delete_service(self, service_id):
        session = self.get_session()
        _service = session.query(Service).filter_by(id=service_id).first()
        with session.begin():
            session.delete(_service)
            session.flush()

    def create_service(self, context, service_ref):
        session = self.get_session()
        with session.begin():
            _service = Service.from_dict(service_ref)
            session.add(_service)
            session.flush()
        return _service.to_dict()

    def service_exists(self, service_id):
        session = self.get_session()
        if not session.query(Service).filter_by(id=service_id).first():
            return False
        return True

    # Service Endpoint Associations
    def add_association(self, endpoint_id, service_id):
        session = self.get_session()
        assoc = {'service_id': service_id,
                 'endpoint_id': endpoint_id}
        assoc_ref = ServiceEndpointAssociation.from_dict(assoc)
        with session.begin():
            session.add(assoc_ref)
            session.flush()

    def remove_association(self, endpoint_id):
        session = self.get_session()
        assoc_ref = session.query(ServiceEndpointAssociation).filter_by(
                              endpoint_id=endpoint_id).first()
        with session.begin():
            session.delete(assoc_ref)
            session.flush

    # Endpoints
    def create_endpoint(self, context, endpoint_ref):
        session = self.get_session()
        service_id = endpoint_ref.pop('service_id')

        new_endpoint = Endpoint.from_dict(endpoint_ref)
        with session.begin():
            session.add(new_endpoint)
            session.flush()
        self.add_association(endpoint_ref['id'], service_id)
        return new_endpoint.to_dict()

    def delete_endpoint(self, endpoint_id):
        session = self.get_session()
        endpoint_ref = session.query(Endpoint).filter_by(
                            id=endpoint_id).first()
        if not endpoint_ref:
            raise exception.NotFound("Endpoint not found")
        self.remove_association(endpoint_id)
        with session.begin():
            session.delete(endpoint_ref)
            session.flush()

    def get_endpoint(self, endpoint_ref):
        return endpoint_ref.to_dict()

    def list_endpoints(self):
        session = self.get_session()
        _endpoints = session.query(Endpoint)
        return list(_endpoints)

    def list_endpoints_with_association(self):
        """ Returns a list of endpoint dicts with associated service_id """
        session = self.get_session()
        o = []
        for e in self.list_endpoints():
            _assoc = session.query(ServiceEndpointAssociation).filter_by(
                                   endpoint_id=e['id']).first()
            ep = e.to_dict()
            ep['service_id'] = _assoc['service_id']
            o.append(ep)
        return o

    def get_catalog(self, user_id, tenant_id, metadata=None):
        d = {'tenant_id': tenant_id, 'user_id': user_id}
        catalog = {}

        for ep in self.list_endpoints_with_association():
            service = self.get_service_by_id(ep['service_id'])
            srv_type = service['type']
            srv_name = service['name']
            region = ep['region']

            if region not in catalog:
                catalog[region] = {}

            catalog[region][srv_type] = {}

            internal_url = ep['internalurl'].replace('$(', '%(')
            public_url = ep['publicurl'].replace('$(', '%(')
            admin_url = ep['adminurl'].replace('$(', '%(')
            catalog[region][srv_type]['name'] = srv_name
            catalog[region][srv_type]['publicURL'] = public_url % d
            catalog[region][srv_type]['adminURL'] = admin_url % d
            catalog[region][srv_type]['internalURL'] = internal_url % d

        return catalog
