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

from keystone.common.sql import upgrades


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    if upgrades.USE_TRIGGERS:
        if migrate_engine.name == 'postgresql':
            drop_reg_trigger_stmt = (
                'DROP TRIGGER registered_limit_insert_trigger on '
                'registered_limit;')
            drop_limit_trigger_stmt = (
                'DROP TRIGGER limit_insert_trigger on limit;')
        elif migrate_engine.name == 'mysql':
            drop_reg_trigger_stmt = (
                'DROP TRIGGER registered_limit_insert_trigger;')
            drop_limit_trigger_stmt = (
                'DROP TRIGGER limit_insert_trigger;')
        else:
            drop_reg_trigger_stmt = (
                'DROP TRIGGER IF EXISTS registered_limit_insert_trigger;')
            drop_limit_trigger_stmt = (
                'DROP TRIGGER IF EXISTS limit_insert_trigger;')
        migrate_engine.execute(drop_reg_trigger_stmt)
        migrate_engine.execute(drop_limit_trigger_stmt)

    registered_limit_table = sql.Table('registered_limit', meta, autoload=True)
    registered_limit_table.c.id.drop()
    registered_limit_table.c.new_id.alter(name='id')

    limit_table = sql.Table('limit', meta, autoload=True)
    limit_table.c.id.drop()
    limit_table.c.new_id.alter(name='id')
