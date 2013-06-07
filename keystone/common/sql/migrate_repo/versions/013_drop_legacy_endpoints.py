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

from keystone.common.sql import migration_helpers


def rename_temporarily_remove_constraints(meta, from_table, to_table_name):
    # DB2 doesn't support renaming a table that has foreign key constraints on
    # it, so drop FK constraints before renaming and then add back afterwards.

    service_table = sql.Table('service', meta, autoload=True)

    constraints = [{'table': from_table,
                    'fk_column': 'service_id',
                    'ref_column': service_table.c.id}]

    migration_helpers.remove_constraints(constraints)

    from_table.rename(to_table_name)

    migration_helpers.add_constraints(constraints)


def upgrade(migrate_engine):
    """Replace API-version specific endpoint tables with one based on v3."""
    meta = sql.MetaData()
    meta.bind = migrate_engine

    legacy_table = sql.Table('endpoint_v2', meta, autoload=True)
    legacy_table.drop()

    new_table = sql.Table('endpoint_v3', meta, autoload=True)

    if migrate_engine.name == 'ibm_db_sa':
        rename_temporarily_remove_constraints(meta, new_table, 'endpoint')
    else:
        new_table.rename('endpoint')


def downgrade(migrate_engine):
    """Create API-version specific endpoint tables."""
    meta = sql.MetaData()
    meta.bind = migrate_engine

    new_table = sql.Table('endpoint', meta, autoload=True)

    if migrate_engine.name == 'ibm_db_sa':
        rename_temporarily_remove_constraints(meta, new_table, 'endpoint_v3')
    else:
        new_table.rename('endpoint_v3')

    sql.Table('service', meta, autoload=True)
    legacy_table = sql.Table(
        'endpoint_v2',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('region', sql.String(255)),
        sql.Column('service_id',
                   sql.String(64),
                   sql.ForeignKey('service.id'),
                   nullable=False),
        sql.Column('extra', sql.Text()))
    legacy_table.create(migrate_engine, checkfirst=True)
