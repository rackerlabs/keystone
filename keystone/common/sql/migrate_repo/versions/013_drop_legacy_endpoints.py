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

from migrate.changeset.constraint import ForeignKeyConstraint
import sqlalchemy as sql


def rename_db2(meta, from_table, to_table):
    # Need to drop constraints before renaming the table.
    old_table = sql.Table(from_table, meta, autoload=True)

    # drop foreign key constraint before rename the table
    service_table = sql.Table('service', meta, autoload=True)

    fkeys = list(old_table.c.service_id.foreign_keys)
    if fkeys:
        fkey_name = fkeys[0].constraint.name
        fkey = ForeignKeyConstraint(columns=[old_table.c.service_id],
                                    refcolumns=[service_table.c.id],
                                    name=fkey_name)
        fkey.drop()

    old_table.rename(to_table)

    # add foreign key constraint back
    if fkeys:
        new_table = sql.Table(to_table, meta, autoload=True)
        fkey = ForeignKeyConstraint(columns=[new_table.c.service_id],
                                    refcolumns=[service_table.c.id],
                                    name=fkey_name)
        fkey.create()


def upgrade(migrate_engine):
    """Replace API-version specific endpoint tables with one based on v3."""
    meta = sql.MetaData()
    meta.bind = migrate_engine

    legacy_table = sql.Table('endpoint_v2', meta, autoload=True)
    legacy_table.drop()

    if migrate_engine.name == 'ibm_db_sa':
        rename_db2(meta, 'endpoint_v3', 'endpoint')
    else:
        new_table = sql.Table('endpoint_v3', meta, autoload=True)
        new_table.rename('endpoint')


def downgrade(migrate_engine):
    """Create API-version specific endpoint tables."""
    meta = sql.MetaData()
    meta.bind = migrate_engine

    if migrate_engine.name == 'ibm_db_sa':
        rename_db2(meta, 'endpoint', 'endpoint_v3')
    else:
        new_table = sql.Table('endpoint', meta, autoload=True)
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
