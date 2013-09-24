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
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    meta = sql.MetaData()
    meta.bind = migrate_engine

    quotas_table = sql.Table(
        'quota',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('resource', sql.String(255), unique=False, nullable=False),
        sql.Column('ceiling', sql.Integer, nullable=False),
        sql.Column('available', sql.Integer, nullable=True),
        sql.Column('created_at', sql.DateTime, nullable=False),
        sql.Column('created_by', sql.String(255), nullable=False),
        sql.Column('closed_at', sql.DateTime, nullable=True),
        sql.Column('closed_by', sql.String(255), nullable=True))
    quotas_table.create(migrate_engine, checkfirst=True)

    child_field_data_table = sql.Table(
        'child_field_data',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('quota_id', sql.String(64), sql.ForeignKey('quota.id'),
                   nullable=False),
        sql.Column('key', sql.Text, nullable=False),
        sql.Column('value', sql.Text, nullable=False))
    child_field_data_table.create(migrate_engine, checkfirst=True)

    parent_field_data_table = sql.Table(
        'parent_field_data',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('quota_id', sql.String(64), sql.ForeignKey('quota.id'),
                   nullable=False),
        sql.Column('key', sql.Text, nullable=False),
        sql.Column('value', sql.Text, nullable=False))
    parent_field_data_table.create(migrate_engine, checkfirst=True)

    h_quotas_table = sql.Table(
        'h_quota',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('quota_id', sql.String(64), sql.ForeignKey('quota.id'),
                   nullable=False),
        sql.Column('updated_at', sql.DateTime, nullable=True),
        sql.Column('updated_by', sql.Text, nullable=False),
        sql.Column('remark', sql.Text, nullable=False))
    h_quotas_table.create(migrate_engine, checkfirst=True)


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    # Operations to reverse the above upgrade go here.
    for table_name in ['quota', 'h_quota', 'child_field_data',
                       'parent_field_data']:
        table = sql.Table(table_name, meta, autoload=True)
        table.drop()
