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

from keystone.common import sql
from keystone import exception
from keystone.limits.backends import base


class LimitModel(sql.ModelBase, sql.ModelDictMixinWithExtras):
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
                              sql.ForeignKey('registered_limits.service_id'))
    region = sql.Column(sql.String(64),
                        sql.ForeignKey('registered_limits.region_id'))
    resource_name = sql.Column(
        sql.String(255),
        sql.ForeignKey('registered_limits.resource_name'),
        nullable=False)
    resource_limit = sql.Column(sql.Integer, nullable=False)


class Limit(base.LimitDriverBase):

    @sql.handle_conflicts(conflict_type='limit')
    def create_limit(self, limit):
        with sql.session_for_write() as session:
            ref = LimitModel.from_dict(limit)
            session.add(ref)
            return ref.to_dict()

    def list_limits(self):
        with sql.session_for_read() as session:
            limits = session.query(LimitModel)
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
