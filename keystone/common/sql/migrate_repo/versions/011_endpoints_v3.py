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


def rename_db2(meta, from_table, to_table_name):
    # DB2 doesn't support renaming a table that has foreign key constraints on
    # it, so drop FK constraints before renaming and then add back afterwards.

    service_table = sql.Table('service', meta, autoload=True)

    fkeys = list(from_table.c.service_id.foreign_keys)
    if fkeys:
        fkey_name = fkeys[0].constraint.name
        fkey = ForeignKeyConstraint(columns=[from_table.c.service_id],
                                    refcolumns=[service_table.c.id],
                                    name=fkey_name)
        fkey.drop()

    from_table.rename(to_table_name)

    # add foreign key constraint back
    if fkeys:
        new_table = sql.Table(to_table_name, meta, autoload=True)
        fkey = ForeignKeyConstraint(columns=[new_table.c.service_id],
                                    refcolumns=[service_table.c.id])
        fkey.create()


def upgrade(migrate_engine):
    """Create API-version specific endpoint tables."""
    meta = sql.MetaData()
    meta.bind = migrate_engine

    legacy_table = sql.Table('endpoint', meta, autoload=True)

    if migrate_engine.name == 'ibm_db_sa':
        rename_db2(meta, legacy_table, 'endpoint_v2')
    else:
        legacy_table.rename('endpoint_v2')

    sql.Table('service', meta, autoload=True)
    new_table = sql.Table(
        'endpoint_v3',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('legacy_endpoint_id', sql.String(64)),
        sql.Column('interface', sql.String(8), nullable=False),
        sql.Column('region', sql.String(255)),
        sql.Column('service_id',
                   sql.String(64),
                   sql.ForeignKey('service.id'),
                   nullable=False),
        sql.Column('url', sql.Text(), nullable=False),
        sql.Column('extra', sql.Text()))
    new_table.create(migrate_engine, checkfirst=True)


def downgrade(migrate_engine):
    """Replace API-version specific endpoint tables with one based on v2."""
    meta = sql.MetaData()
    meta.bind = migrate_engine

    new_table = sql.Table('endpoint_v3', meta, autoload=True)
    new_table.drop()

    legacy_table = sql.Table('endpoint_v2', meta, autoload=True)

    if migrate_engine.name == 'ibm_db_sa':
        rename_db2(meta, legacy_table, 'endpoint')
    else:
        legacy_table.rename('endpoint')
