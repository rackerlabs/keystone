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


# Migration 105 clean-up.
# To avoid other errors during a multi-node migration legacy migration 105
# doesn't set the created_at column to be non-nullable to match how the
# sql_model is defined - this is fixed up here.


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    password_table = sql.Table('password', meta, autoload=True)
    password_table.c.created_at.alter(nullable=False)

    if migrate_engine.name == 'postgresql':
        stmnt = 'DROP TRIGGER IF EXISTS password_created_at ON password;'
    else:
        stmnt = 'DROP TRIGGER IF EXISTS password_created_at;'
    migrate_engine.execute(stmnt)
