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


def upgrade(migrate_engine):

    meta = sql.MetaData()
    meta.bind = migrate_engine

    if migrate_engine.name == 'mysql':
        sql_tmpl = 'ALTER TABLE %s ENGINE=InnoDB;'
        table_names = 'consumer', 'request_token', 'access_token'
        sql_query = ' '.join([sql_tmpl % i for i in table_names])
        migrate_engine.execute(sql_query)

        request_token = sql.Table('request_token', meta, autoload=True)
        consumer = sql.Table('consumer', meta, autoload=True)
        access_token = sql.Table('access_token', meta, autoload=True)

        constraints = [{'table': request_token,
                        'fk_column': 'consumer_id',
                        'ref_column': consumer.c.id},
                       {'table': access_token,
                        'fk_column': 'consumer_id',
                        'ref_column': consumer.c.id}]

        migration_helpers.add_constraints(constraints)


def downgrade(migrate_engine):

    meta = sql.MetaData()
    meta.bind = migrate_engine

    if migrate_engine.name == 'mysql':
        sql_tmpl = 'ALTER TABLE %s ENGINE=MyISAM;'
        table_names = 'consumer', 'request_token', 'access_token'
        sql_query = ' '.join([sql_tmpl % i for i in table_names])
        migrate_engine.execute(sql_query)

        request_token = sql.Table('request_token', meta, autoload=True)
        consumer = sql.Table('consumer', meta, autoload=True)
        access_token = sql.Table('access_token', meta, autoload=True)

        constraints = [{'table': request_token,
                        'fk_column': 'consumer_id',
                        'ref_column': consumer.c.id},
                       {'table': access_token,
                        'fk_column': 'consumer_id',
                        'ref_column': consumer.c.id}]

        migration_helpers.remove_constraints(constraints)
