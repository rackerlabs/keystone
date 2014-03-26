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
from keystone.contrib import endpoint_filter
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
    filters = sql.Column(sql.JsonBlob())


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
    __tablename__ = 'project_user_endpoint_group'
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


class EndpointGrouping(object):
    # Internal interface to manage the database

    def db_sync(self, version=None):
        abs_path = migration_helpers.find_migrate_repo(endpoint_grouping)
        migration.db_sync(sql.get_engine(), abs_path, version=version)

    @sql.handle_conflicts(conflict_type='project_endpoint')
    def add_endpoint_group_to_project(self, endpoint_group_id, project_id):

