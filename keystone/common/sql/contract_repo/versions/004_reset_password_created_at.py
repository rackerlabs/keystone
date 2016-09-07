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


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    if migration_helpers.USE_TRIGGERS:
        if migrate_engine.name == 'postgresql':
            drop_insert_trigger = (
                'DROP TRIGGER IF EXISTS password_created_at_new on password;'
            )
        elif migrate_engine.name == 'mysql':
            drop_insert_trigger = (
                'DROP TRIGGER IF EXISTS password_created_at_new;'
            )
        else:
            drop_insert_trigger = (
                'DROP TRIGGER IF EXISTS password_created_at_new;'
            )
        migrate_engine.execute(drop_insert_trigger)

    password = sql.Table('password', meta, autoload=True)
    password.c.created_at.drop()
    password.c.created_at_new.alter(nullable=False)
    password.c.created_at_new.alter(name='created_at')
