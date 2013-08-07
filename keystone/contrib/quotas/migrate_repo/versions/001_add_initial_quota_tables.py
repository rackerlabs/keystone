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

import sqlalchemy as sql


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    sql.Table('user', meta, autoload=True)
    sql.Table('role', meta, autoload=True)
    sql.Table('project', meta, autoload=True)

    resource_table = sql.Table(
        'resource',
        meta,
        sql.Column('id', sql.String(64), primary_key=True, nullable=False),
        sql.Column('name', sql.String(64), unique=True, nullable=False),
        sql.Column('default_limit', sql.Integer, nullable=False),
        sql.Column('description', sql.String(255)))

    resource_table.create(migrate_engine, checkfirst=True)

    project_quota_table = sql.Table(
        'project_quota',
        meta,
        sql.Column('id', sql.String(64), primary_key=True, nullable=False),
        sql.Column('project_id', sql.String(64), nullable=False),
        sql.Column('resource_id', sql.String(64),
            sql.ForeignKey('resource.id'), nullable=False),
        sql.Column('limit', sql.Integer, nullable=False))

    project_quota_table.create(migrate_engine, checkfirst=True)

    user_quota_table = sql.Table(
        'user_quota',
        meta,
        sql.Column('id', sql.String(64), primary_key=True, nullable=False),
        sql.Column('user_id', sql.String(64), nullable=False),
        sql.Column('resource_id', sql.String(64),
            sql.ForeignKey('resource.id'), nullable=False),
        sql.Column('limit', sql.Integer, nullable=False))

    user_quota_table.create(migrate_engine, checkfirst=True)


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    for table_name in ['resource', 'project_quota', 'user_quota']:
        table = sql.Table(table_name, meta, autoload=True)
        table.drop()
