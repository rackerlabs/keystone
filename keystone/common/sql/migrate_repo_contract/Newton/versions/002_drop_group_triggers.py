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
# In a multi-node migration, this could leave the created_at attribute
# unset. In addition, to avoid other errors during a multi-node
# migration it doesn't set the created_at column to be non-nullable to
# match how the sql_model is defined.


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    stmnt = 'DROP TRIGGER group2togroup;'
    migrate_engine.execute(stmnt)

    stmnt = 'DROP TRIGGER grouptogroup2;'
    migrate_engine.execute(stmnt)
