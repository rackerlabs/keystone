# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
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


class EpFilter(sql.ModelBase, sql.DictBase):
    """Endpoint filtering join table."""
    __tablename__ = 'endpoint_filter'
    endpoint_id = sql.Column(sql.String(64),
                             sql.ForeignKey('endpoint.id'),
                             primary_key=True)
    project_id = sql.Column(sql.String(64),
                            sql.ForeignKey('project.id'),
                            primary_key=True)


#class EndpointFilter(sql.Base, endpoint_filter.Driver):
class EndpointFilter(sql.Base):
    # Internal interface to manage the database

    def db_sync(self, version=None):
        migration.db_sync(version=version)

    def create_ep_filter_association(self, endpoint_id, project_id):
        session = self.get_session()
        query = session.query(EpFilter)
        query = query.filter_by(endpoint_id=endpoint_id)
        query = query.filter_by(project_id=project_id)
        rv = query.first()
        if rv:
            return
        with session.begin():
            session.add(EpFilter(endpoint_id=endpoint_id,
                                 project_id=project_id))
            session.flush()

    def check_endpoint_in_project(self, endpoint_id, project_id):
        session = self.get_session()
        query = session.query(EpFilter)
        query = query.filter_by(endpoint_id=endpoint_id)
        query = query.filter_by(project_id=project_id)
        if query:
            return

    def remove_ep_filter_association(self, endpoint_id, project_id):
        session = self.get_session()
        query = session.query(EpFilter)
        query = query.filter_by(endpoint_id=endpoint_id)
        query = query.filter_by(project_id=project_id)
        association_ref = query.first()
        if association_ref is None:
            raise exception.NotFound('Endpoint not associated with Project')
        with session.begin():
            session.delete(association_ref)
            session.flush()

    def list_endpoints_in_project(self, project_id):
        session = self.get_session()
        query = session.query(EpFilter)
        query = query.filter_by(project_id=project_id)
        association_refs = query.all()
        return association_refs

    def list_project_endpoints(self, endpoint_id):
        session = self.get_session()
        query = session.query(EpFilter)
        query = query.filter_by(endpoint_id=endpoint_id)
        association_refs = query.all()
        return association_refs
