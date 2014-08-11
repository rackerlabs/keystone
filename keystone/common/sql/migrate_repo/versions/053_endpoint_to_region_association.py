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


"""Adds an `name` column to the `region` table. And 'region' column in the
'endpoint' table is renamed to 'region_id' to make it as foreign key to
respective 'region'.

To Upgrade:

Endpoint Table

a. Add an region_id column
b. For each endpoint
    i. Migrate all the region in endpoint table into region table
    ii. Add the id to the region_id
c. Remove the column region


To Downgrade:

Endpoint Table

a. Add an region column
b. For each endpoint
    i. Get the region name from region table and update in region
    column
c. Remove the column region_id
"""

import migrate
import sqlalchemy as sql
from sqlalchemy.orm import sessionmaker


def _migrate_to_region_id(migrate_engine, region_table, endpoint_table):
    endpoints = list(endpoint_table.select().execute())

    for endpoint in endpoints:
        region = list(region_table.select(
            whereclause=region_table.c.id == endpoint.region).execute())
        if len(region) == 1:
            region_id = region[0].id
        else:
            region_id = endpoint.region
            region = {'id': region_id,
                      'description': '',
                      'extra': '{}'}
            session = sessionmaker(bind=migrate_engine)()
            region_table.insert(region).execute()
            session.commit()

        new_values = {'region_id': region_id}
        f = endpoint_table.c.id == endpoint.id
        update = endpoint_table.update().where(f).values(new_values)
        migrate_engine.execute(update)

    migrate.ForeignKeyConstraint(
        columns=[endpoint_table.c.region_id],
        refcolumns=[region_table.c.id],
        name='fk_endpoint_region_id').create()


def _migrate_to_region(migrate_engine, region_table, endpoint_table):
    endpoints = list(endpoint_table.select().execute())

    for endpoint in endpoints:
        region = list(region_table.select(
            whereclause=region_table.c.id == endpoint.region_id).execute())
        new_values = {'region': region[0].id}
        f = endpoint_table.c.id == endpoint.id
        update = endpoint_table.update().where(f).values(new_values)
        migrate_engine.execute(update)

    if 'sqlite' != migrate_engine.name:
        migrate.ForeignKeyConstraint(
            columns=[endpoint_table.c.region_id],
            refcolumns=[region_table.c.id],
            name='fk_endpoint_region_id').drop()
    endpoint_table.c.region_id.drop()


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    region_table = sql.Table('region', meta, autoload=True)
    endpoint_table = sql.Table('endpoint', meta, autoload=True)
    region_id_column = sql.Column('region_id',
                                  sql.String(length=64), nullable=True)
    region_id_column.create(endpoint_table)

    _migrate_to_region_id(migrate_engine, region_table, endpoint_table)

    endpoint_table.c.region.drop()


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    region_table = sql.Table('region', meta, autoload=True)
    endpoint_table = sql.Table('endpoint', meta, autoload=True)
    region_column = sql.Column('region',
                               sql.String(length=255))
    region_column.create(endpoint_table)

    _migrate_to_region(migrate_engine, region_table, endpoint_table)

    region_table.delete().execute()
