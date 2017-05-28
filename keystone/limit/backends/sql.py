# Copyright 2017 SUSE Linux Gmbh
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

from keystone.common import driver_hints
from keystone.common import sql
from keystone import exception
from keystone.limits.backends import base


from keystone.catalog.backends.sql import Region, Service
from keystone.resource.backends.sql import Project

class RegisteredLimitModel(sql.ModelBase, sql.ModelDictMixin):
    __tablename__ = 'registered_limit'
    attributes = [
        'service_type', 'region', 'resource_name', 'project_default'
    ]

    service_type = sql.Column(sql.String(255),
                              sql.ForeignKey('service.id'),
                              primary_key=True)
    region = sql.Column(sql.String(64),
                        sql.ForeignKey('region.id'),
                        primary_key=True)
    resource_name = sql.Column(sql.String(255), primary_key=True)
    project_default = sql.Column(sql.Integer, nullable=False)



class LimitModel(sql.ModelBase, sql.ModelDictMixin):
    __tablename__ = 'limit'
    attributes = [
        'project_id',
        'service_type',
        'region',
        'resource_name',
        'resource_limit'
    ]

    project_id = sql.Column(sql.String(64),
                            sql.ForeignKey('project.id'),
                            primary_key=True)
    service_type = sql.Column(sql.String(255),
                              sql.ForeignKey('registered_limit.service_type'),
                              primary_key=True)
    region = sql.Column(sql.String(64),
                        sql.ForeignKey('registered_limit.region'),
                        primary_key=True)
    resource_name = sql.Column(
        sql.String(255),
        sql.ForeignKey('registered_limit.resource_name'),
        primary_key=True)
    resource_limit = sql.Column(sql.Integer, nullable=False)


class RegisteredLimit(base.RegisteredLimitDriverBase):

    @sql.handle_conflicts(conflict_type='registered_limit')
    def create_registered_limit(self, registered_limit):
        with sql.session_for_write() as session:
            ref = RegisteredLimitModel.from_dict(registered_limit)
            session.add(ref)
            return ref.to_dict()

    @driver_hints.truncated
    def list_registered_limits(self, hints):
        with sql.session_for_read() as session:
            registered_limits = session.query(RegisteredLimitModel)
            registered_limits = sql.filter_limit_query(RegisteredLimitModel,
                                                       registered_limits,
                                                       hints)
            return [s.to_dict() for s in registered_limits]

    def _get_registered_limit(self, session, service_type, region,
                              resource_name):
        ref = session.query(RegisteredLimitModel).get([service_type,
                                                       region,
                                                       resource_name])
        if ref is None:
            raise exception.RegisteredLimitNotFound(
                service_type=service_type,
                region=region,
                resource_name=resource_name)
        return ref

    def get_registered_limit(self, service_type, region, resource_name):
        with sql.session_for_read() as session:
            return self._get_registered_limit(session,
                                              service_type,
                                              region,
                                              resource_name).to_dict()

    @sql.handle_conflicts(conflict_type='registered_limit')
    def update_registered_limit(self, registered_limit):
        with sql.session_for_write() as session:
            ref = self._get_registered_limit(session,
                                             registered_limit['service_type'],
                                             registered_limit['region'],
                                             registered_limit['resource_name'])
            old_dict = ref.to_dict()
            old_dict['project_default'] = registered_limit['project_default']
            new_registered_limit = RegisteredLimitModel.from_dict(old_dict)
            ref.project_default = new_registered_limit.project_default
            return ref.to_dict()

    def delete_registered_limit(self, service_type, region, resource_name):
        with sql.session_for_write() as session:
            ref = self._get_registered_limit(session,
                                             service_type,
                                             region,
                                             resource_name)
            session.delete(ref)

class Limit(base.LimitDriverBase):

    @sql.handle_conflicts(conflict_type='limit')
    def create_limit(self, limit):
        with sql.session_for_write() as session:
            ref = LimitModel.from_dict(limit)
            session.add(ref)
            return ref.to_dict()

    @driver_hints.truncated
    def list_limits(self, hints):
        with sql.session_for_read() as session:
            limits = session.query(LimitModel)
            limits = sql.filter_limit_query(LimitModel,
                                            limits,
                                            hints)
            return [s.to_dict() for s in limits]

    def _get_limit(self, session, project_id, service_type, region,
                   resource_name):
        ref = session.query(LimitModel).get(
            [project_id, service_type, region, resource_name])
        if ref is None:
            raise exception.LimitNotFound(
                project_id=project_id, service_type=service_type,
                region=region, resource_name=resource_name)
        return ref

    def get_limit(self, project_id, service_type, region, resource_name):
        with sql.session_for_read() as session:
            return self._get_limit(session,
                                   project_id,
                                   service_type,
                                   region,
                                   resource_name).to_dict()

    @sql.handle_conflicts(conflict_type='limit')
    def update_limit(self, limit):
        with sql.session_for_write() as session:
            ref = self._get_limit(session,
                                  limit['project_id'],
                                  limit['service_type'],
                                  limit['region'],
                                  limit['resource_name'])
            old_dict = ref.to_dict()
            old_dict['resource_limit'] = limit['resource_limit']
            new_limit = LimitModel.from_dict(old_dict)
            ref.resource_limit = new_limit.resource_limit
            return ref.to_dict()

    def delete_limit(self, project_id, service_type, region, resource_name):
        with sql.session_for_write() as session:
            ref = self._get_limit(session,
                                  project_id,
                                  service_type,
                                  region,
                                  resource_name)
            session.delete(ref)
