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

import sqlalchemy as sql


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    meta = sql.MetaData()
    meta.bind = migrate_engine

    endpoint_group_table = sql.Table(
        'endpoint_group',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(255)),
        sql.Column('description', sql.String(255)),
        sql.Column('filters', sql.JsonBlob()))
    endpoint_group_table.create(migrate_engine, checkfirst=True)

    project_endpoint_group_table = sql.Table(
        'project_endpoint_group',
        meta,
        sql.Column('endpoint_group_id', sql.String(64),
                   primary_key=True, nullable=False),
        sql.Column('project_id', sql.String(64),
                   primary_key=True, nullable=False))
    project_endpoint_group_table.create(migrate_engine, checkfirst=True)

    user_project_endpoint_group_table = sql.Table(
        'user_project_endpoint_group',
        meta,
        sql.Column('endpoint_group_id', sql.String(64),
                   primary_key=True, nullable=False),
        sql.Column('project_id', sql.String(64),
                   primary_key=True, nullable=False),
        sql.Column('user_id', sql.String(64),
                   primary_key=True, nullable=False))
    user_project_endpoint_group_table.create(migrate_engine, checkfirst=True)


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    meta = sql.MetaData()
    meta.bind = migrate_engine

    tables = ['endpoint_group','project_endpoint_group',
              'user_project_endpoint_group']
    for t in tables:
        table = sql.Table(t, meta, autoload=True)
        table.drop(migrate_engine, checkfirst=True)
