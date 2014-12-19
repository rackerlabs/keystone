# Copyright 2014 IBM Corp.
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

    myfirstabac_user_attr_table = sql.Table(
        'myfirstabac_user_attributes',
        meta,
        sql.Column(
            'user_id',
            sql.String(64),
            primary_key=True,
            nullable=False),
        sql.Column(
            'user_id',
            sql.Integer,
            nullable=True))

    myfirstabac_user_attr_table.create(migrate_engine, checkfirst=True)

    myfirstabac_project_attr_table = sql.Table(
        'myfirstabac_project_attributes',
        meta,
        sql.Column(
            'project_id',
            sql.String(64),
            primary_key=True,
            nullable=False),
        sql.Column(
            'role_for_eighteen_or_over',
            sql.String(64),
            nullable=True),
        sql.Column(
            'role_for_under_eighteen',
            sql.String(64),
            nullable=True))

    myfirstabac_project_attr_table.create(migrate_engine, checkfirst=True)


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    # Operations to reverse the above upgrade go here.
    for table_name in ['myfirstabac_project_attributes',
                       'myfirstabac_user_attributes']:
        table = sql.Table(table_name, meta, autoload=True)
        table.drop()
