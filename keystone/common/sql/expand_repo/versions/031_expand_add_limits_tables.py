# Copyright 2017 SUSE Linux Gmbh
# Copyright 2017 Huawei
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

import migrate
import sqlalchemy as sql


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    service_table = sql.Table('service', meta, autoload=True)
    region_table = sql.Table('region', meta, autoload=True)
    project_table = sql.Table('project', meta, autoload=True)

    registered_limit_table = sql.Table(
        'registered_limit',
        meta,
        sql.Column('service_type',
                   sql.String(255),
                   sql.ForeignKey(service_table.c.id),
                   primary_key=True),
        sql.Column('region',
                   sql.String(64),
                   sql.ForeignKey(region_table.c.id),
                   primary_key=True),
        sql.Column('resource_name', sql.String(255), primary_key=True),
        sql.Column('default_limit', sql.Integer, nullable=False),
        mysql_engine='InnoDB',
        mysql_charset='utf8')
    registered_limit_table.create(migrate_engine, checkfirst=True)

    limit_table = sql.Table(
        'limit',
        meta,
        sql.Column('project_id',
                   sql.String(64),
                   sql.ForeignKey(project_table.c.id),
                   primary_key=True),
        sql.Column('service_type', sql.String(255), primary_key=True),
        sql.Column('region', sql.String(64), primary_key=True),
        sql.Column('resource_name', sql.String(255), primary_key=True),
        sql.Column('resource_limit', sql.Integer, nullable=False),
        mysql_engine='InnoDB',
        mysql_charset='utf8')
    limit_table.create(migrate_engine, checkfirst=True)

    migrate.ForeignKeyConstraint(
        columns=[limit_table.c.service_type,
                 limit_table.c.region,
                 limit_table.c.resource_name],
        refcolumns=[registered_limit_table.c.service_type,
                    registered_limit_table.c.region,
                    registered_limit_table.c.resource_name]).create()
