# vim: tabstop=4 shiftwidth=4 softtabstop=4

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
    meta = sql.MetaData()
    meta.bind = migrate_engine

    mapping_table = sql.Table(
        'mapping',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(255), nullable=False),
        sql.Column('extra', sql.Text(), nullable=True))

    mapping_table.create(migrate_engine, checkfirst=True)

    rules_table = sql.Table(
        'rule',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('mapping_id', sql.String(64),
                   sql.ForeignKey('mapping.id', ondelete='CASCADE'),
                   nullable=False),
        sql.Column('extra', sql.Text(), nullable=True))

    rules_table.create(migrate_engine, checkfirst=True)

    local_attribute_table = sql.Table(
        'local_attribute',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('rule_id', sql.String(64),
                   sql.ForeignKey('rule.id', ondelete='CASCADE'),
                   nullable=False),
        sql.Column('ks_object', sql.String(64), nullable=True, unique=False),
        sql.Column('extra', sql.Text(), nullable=True))

    local_attribute_table.create(migrate_engine, checkfirst=True)

    remote_attribute_table = sql.Table(
        'remote_attribute',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('rule_id', sql.String(64),
                   sql.ForeignKey('rule.id', ondelete='CASCADE'),
                   nullable=False),
        sql.Column('type', sql.String(64), nullable=False, unique=False),
        sql.Column('requirement', sql.String(64),
                   nullable=False, unique=False),
        sql.Column('values', sql.Text(), nullable=True, unique=False),
        sql.Column('extra', sql.Text(), nullable=True))

    remote_attribute_table.create(migrate_engine, checkfirst=True)


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    # Drop previously created tables
    tables = ['mapping', 'rule', 'local_attribute',
              'remote_attribute']
    for table_name in tables:
        table = sql.Table(table_name, meta, autoload=True)
        table.drop()
