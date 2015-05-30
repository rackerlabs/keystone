# Copyright 2014 Hewlett-Packard Company
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

import sqlalchemy as sql

from keystone.common.sql import migration_helpers


def upgrade(migrate_engine):
    try:
        extension_version = migration_helpers.get_db_version(
            extension='endpoint_filter',
            engine=migrate_engine)
    except Exception:
        extension_version = 0

    # This extension corresponds to endpoint_filter extension migration 2. Only
    # update if it has not been run.
    if extension_version >= 2:
        return

    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    meta = sql.MetaData()
    meta.bind = migrate_engine

    endpoint_group_table = sql.Table(
        'endpoint_group',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(255), nullable=False),
        sql.Column('description', sql.Text, nullable=True),
        sql.Column('filters', sql.Text(), nullable=False))
    endpoint_group_table.create(migrate_engine, checkfirst=True)

    project_endpoint_group_table = sql.Table(
        'project_endpoint_group',
        meta,
        sql.Column('endpoint_group_id', sql.String(64),
                   sql.ForeignKey('endpoint_group.id'), nullable=False),
        sql.Column('project_id', sql.String(64), nullable=False),
        sql.PrimaryKeyConstraint('endpoint_group_id',
                                 'project_id'))
    project_endpoint_group_table.create(migrate_engine, checkfirst=True)
