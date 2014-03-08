# Copyright 2014 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


"""Relax the uniqueness of `description` column in region table.

The region table has a dedicated column for the region `description`. This
column originally was not nullable and had to be unique. So if a user wanted
to create a region without sending a `description` in the request, they would
experience an SQL error because the `description` column can't be null for a
region. This means that every region had to have a unique description.

To upgrade, we are going to transfer all the data from the existing region
table to a temporary table, drop the original region table, and recreate
a new region table with unique not set on the `description` column. Finally,
place all the data from the temporary table into the new region table and drop
the temporary region table.

To downgrade, we are essentially going to do the opposite, but if we hit the
case where we are downgrading with regions in the database that have the same
value in the `description` column, we will modify the `description` with the
ID of the region so that each region has a unique `description` before
reapplying the unique constraint.

"""

import sqlalchemy as sql
from sqlalchemy.orm import sessionmaker


def _migrate_to_new_region_table(meta, migrate_engine, session):
    # Create a temporary region table to hold data while we recreate the
    # new region table without a unique constraint on the description column
    temp_region_table = sql.Table(
        'temp_region',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('description', sql.String(255), nullable=False),
        sql.Column('parent_region_id', sql.String(64), nullable=True),
        sql.Column('extra', sql.Text()))
    temp_region_table.create(migrate_engine, checkfirst=True)

    # Migrate data from old region table to temporary region table
    region_table = sql.Table('region', meta, autoload=True)
    for region in session.query(region_table):
        session.execute('insert into temp_region (id, description, '
                        'parent_region_id, extra) values '
                        '( :id, :description, :parent_region_id, :extra);',
                        {'id': region.id,
                         'description': region.description,
                         'parent_region_id': region.parent_region_id,
                         'extra': region.extra})

    # Drop the old region table
    session.execute('drop table region;')

    # Create new region table without unique constraint on description column.
    # We also need to create a new metadata stream since we are going to load
    # a different version of the region table.
    meta2 = sql.MetaData()
    meta2.bind = migrate_engine
    new_region_table = sql.Table(
        'region',
        meta2,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('description', sql.String(255), nullable=False),
        sql.Column('parent_region_id', sql.String(64), nullable=True),
        sql.Column('extra', sql.Text()))
    new_region_table.create(migrate_engine, checkfirst=True)

    # Migrate data from temp_region table to region table
    for region in session.query(temp_region_table):
        session.execute('insert into region (id, description, '
                        'parent_region_id, extra) values '
                        '( :id, :description, :parent_region_id, :extra);',
                        {'id': region.id,
                         'description': region.description,
                         'parent_region_id': region.parent_region_id,
                         'extra': region.extra})

    # Drop the temporary region table
    session.execute('drop table temp_region;')


def _migrate_to_old_region_table(meta, migrate_engine, session):
    # Create a temporary region table to hold data
    temp_region_table = sql.Table(
        'temp_region',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('description', sql.String(255), unique=True,
                   nullable=False),
        sql.Column('parent_region_id', sql.String(64), nullable=True),
        sql.Column('extra', sql.Text()))
    temp_region_table.create(migrate_engine, checkfirst=True)

    # Migrate data from current region table to temporary region table
    region_table = sql.Table('region', meta, autoload=True)
    for region in session.query(region_table):
        try:
            session.execute('insert into temp_region (id, description, '
                            'parent_region_id, extra) values '
                            '( :id, :description, :parent_region_id, :extra);',
                            {'id': region.id,
                             'description': region.description,
                             'parent_region_id': region.parent_region_id,
                             'extra': region.extra})
        except sql.exc.IntegrityError:
            # If we hit this case then we have two regions with the same
            # description, so make the description unique by setting it to the
            # ID of the region and it's description
            description = region.id + '-' + region.description
            session.execute('insert into temp_region (id, description, '
                            'parent_region_id, extra) values '
                            '( :id, :description, :parent_region_id, :extra);',
                            {'id': region.id,
                             'description': description,
                             'parent_region_id': region.parent_region_id,
                             'extra': region.extra})
    # Drop the current region table
    session.execute('drop table region;')

    # Create region table with unique constraint
    # We also need to create a new metadata stream since we are going to load
    # a different version of the region table.
    meta2 = sql.MetaData()
    meta2.bind = migrate_engine
    old_region_table = sql.Table(
        'region',
        meta2,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('description', sql.String(255), unique=True,
                   nullable=False),
        sql.Column('parent_region_id', sql.String(64), nullable=True),
        sql.Column('extra', sql.Text()))
    old_region_table.create(migrate_engine, checkfirst=True)

    # Migrate data from temp_region table to region table
    for region in session.query(temp_region_table):
        session.execute('insert into region (id, description, '
                        'parent_region_id, extra) values '
                        '( :id, :description, :parent_region_id, :extra);',
                        {'id': region.id,
                         'description': region.description,
                         'parent_region_id': region.parent_region_id,
                         'extra': region.extra})
    # Drop the temporary region table
    session.execute('drop table temp_region;')


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    session = sessionmaker(bind=migrate_engine)()

    _migrate_to_new_region_table(meta, migrate_engine, session)
    session.commit()
    session.close()


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    session = sessionmaker(bind=migrate_engine)()

    _migrate_to_old_region_table(meta, migrate_engine, session)
    session.commit()
    session.close()
