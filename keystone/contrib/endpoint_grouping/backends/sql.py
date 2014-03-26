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
from keystone.common.sql import migration_helpers
from keystone.contrib import endpoint_grouping
from keystone import exception
from keystone.openstack.common.db.sqlalchemy import migration
from keystone.openstack.common.gettextutils import _


class EndpointGroup(sql.ModelBase, sql.DictBase):
    """Endpoint Groups table."""
    __tablename__ = 'endpoint_group'
    attributes = ['id', 'name', 'description', 'filters']
    id = sql.Column(sql.String(64), primary_key=True)
    name = sql.Column(sql.String(255), nullable=False)
    description = name = sql.Column(sql.String(255))
    filters = sql.Column(sql.JsonBlob(), nullable=False)

    @classmethod
    def from_dict(cls, dictionary):
        new_dictionary = dictionary.copy()
        return cls(**new_dictionary)

    def to_dict(self):
        """Return a dictionary with model's attributes."""
        d = dict()
        for attr in self.__class__.attributes:
            d[attr] = getattr(self, attr)
        return d


class ProjectEndpointGroupMembership(sql.ModelBase, sql.DictBase):
    """project endpoint group relationship table."""
    __tablename__ = 'project_endpoint_group'
    attributes = ['endpoint_group_id', 'project_id']
    endpoint_group_id = sql.Column(sql.String(64),
                             primary_key=True,
                             nullable=False)
    project_id = sql.Column(sql.String(64),
                            primary_key=True,
                            nullable=False)


class UserProjectEndpointGroupMembership(sql.ModelBase, sql.DictBase):
    """user, project and endpoint group relationship table."""
    __tablename__ = 'user_project_endpoint_group'
    attributes = ['endpoint_group_id', 'project_id', 'user_id']
    endpoint_group_id = sql.Column(sql.String(64),
                             primary_key=True,
                             nullable=False)
    project_id = sql.Column(sql.String(64),
                            primary_key=True,
                            nullable=False)
    user_id = sql.Column(sql.String(64),
                            primary_key=True,
                            nullable=False)


class EndpointGrouping(endpoint_grouping.Driver):
    # Internal interface to manage the database

    def db_sync(self, version=None):
        abs_path = migration_helpers.find_migrate_repo(endpoint_grouping)
        migration.db_sync(sql.get_engine(), abs_path, version=version)

    def create_endpoint_group(self, endpoint_group_id, endpoint_group):
        session = sql.get_session()
        with session.begin():
            endpoint_group_ref = EndpointGroup.from_dict(endpoint_group)
            session.add(endpoint_group_ref)
        return endpoint_group_ref.to_dict()

    def _get_endpoint_group(self, session, endpoint_group_id):
        endpoint_group_ref = session.query(EndpointGroup).get(
            endpoint_group_id)
        if endpoint_group_ref is None:
            msg = _('Endpoint Group %(endpoint_group_id)s not found'
                   ) % {'endpoint_group_id': endpoint_group_id}
            raise exception.NotFound(msg)
        return endpoint_group_ref

    def get_endpoint_group(self, endpoint_group_id):
        session = sql.get_session()
        return _get_endpoint_group(self, session, endpoint_group_id)

    @sql.handle_conflicts(conflict_type='project_endpoint_group')
    def add_endpoint_group_to_project(self, project_id, endpoint_group_id):
        session = sql.get_session()
        with session.begin():
            endpoint_group_project_ref = ProjectEndpointGroupMembership(endpoint_group_id=endpoint_group_id,
                                                  project_id=project_id)
            session.add(endpoint_group_project_ref)

    def check_endpoint_group_in_project(self, project_id, endpoint_group_id):
        session = sql.get_session()
        endpoint_group_project_ref = session.query(ProjectEndpointGroupMembership).get(
            (endpoint_group_id, project_id))
        if endpoint_group_project_ref is None:
            msg = _('Endpoint Group Project Association not found')
            raise exception.NotFound(msg)

    def list_endpoint_groups_for_project(self, project_id):
        session = sql.get_session()
        query = session.query(ProjectEndpointGroupMembership)
        query = query.filter_by(project_id=project_id)
        endpoint_group_refs = query.all()
        return endpoint_group_refs

    @sql.handle_conflicts(conflict_type='user_project_endpoint_group')
    def grant_endpoint_group_in_project_to_user(self, project_id, endpoint_group_id, user_id):
        session = sql.get_session()
        with session.begin():
            endpoint_group_project_user_ref = UserProjectEndpointGroupMembership(
                project_id=project_id, endpoint_group_id=endpoint_group_id,
                user_id=user_id)
            session.add(endpoint_group_project_user_ref)        

    def list_endpoint_groups_in_project_granted_to_user(self, project_id, user_id):
        session = sql.get_session()
        query = session.query(UserProjectEndpointGroupMembership)
        query = query.filter_by(project_id=project_id, user_id=user_id)
        user_project_group_refs = query.all()
        return user_project_group_refs      

    def list_endpoint_groups(self):
        session = sql.get_session()
        query = session.query(EndpointGroup)
        endpoint_group_refs = query.all()
        return endpoint_group_refs   

    def list_projects_for_endpoint_group(self, endpoint_group_id):   
        session = sql.get_session()   
        query = session.query(ProjectEndpointGroupMembership)
        query = query.filter_by(endpoint_group_id=endpoint_group_id)
        endpoint_group_refs = query.all()
        endpoint_group_dict = {"endpoint_group": { "endpoint_group_id": endpoint_group_id, "projects": [] }}
        for endpoint_group_ref in endpoint_group_refs:
            endpoint_group_dict['endpoint_group']['projects'].append({
                'project_id':endpoint_group_ref.project_id
                })
        return endpoint_group_dict   

    def get_filter_for_endpoint_group(self, endpoint_group_id):
        session = sql.get_session()
        endpoint_group_ref = self._get_endpoint_group(session, endpoint_group_id)
        return endpoint_group_ref.filters
