# Copyright 2014 Mirantis.inc
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import sqlalchemy as sql

from keystone.common.sql import migration_helpers


_TABLE_NAMES = 'consumer', 'request_token', 'access_token'
_updated = None


@migration_helpers.only_with_engine('mysql')
def upgrade(migrate_engine):

    meta = sql.MetaData()
    meta.bind = migrate_engine

    global _updated
    _updated = migration_helpers.change_mysql_engine(
        migrate_engine, 'InnoDB', _TABLE_NAMES)

    request_token = sql.Table('request_token', meta, autoload=True)
    access_token = sql.Table('access_token', meta, autoload=True)
    consumer = sql.Table('consumer', meta, autoload=True)

    fk_col = 'consumer_id'
    constraints = []
    for tbl in request_token, access_token:
        if fk_col not in (i.parent.name for i in tbl.foreign_keys):
            constraints.append({'table': tbl,
                                'fk_column': 'consumer_id',
                                'ref_column': consumer.c.id})

    migration_helpers.add_constraints(constraints)


@migration_helpers.only_with_engine('mysql')
def downgrade(migrate_engine):

    meta = sql.MetaData()
    meta.bind = migrate_engine

    if _updated:
        migration_helpers.change_mysql_engine(
            migrate_engine, 'MyISAM', _updated)

        request_token = sql.Table('request_token', meta, autoload=True)
        access_token = sql.Table('access_token', meta, autoload=True)
        consumer = sql.Table('consumer', meta, autoload=True)

        fk_col = 'consumer_id'
        constraints = []
        for tbl in request_token, access_token:
            if fk_col in (i.parent.name for i in tbl.foreign_keys):
                constraints.append({'table': tbl,
                                    'fk_column': 'consumer_id',
                                    'ref_column': consumer.c.id})

        migration_helpers.remove_constraints(constraints)
