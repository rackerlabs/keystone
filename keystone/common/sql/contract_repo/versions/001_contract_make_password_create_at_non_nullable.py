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

import datetime

import sqlalchemy as sql
from sqlalchemy.sql.expression import null


# Migration 105 clean-up.
# In a multi-node migration, this could result in some rows left without
# the create_at value set to the current date. We could solve this issue by
# creating triggers in the expand phase, although given the actual migration
# that caused this problem is in the legacy repo, there would always be a
# chance that a row could have been created before the triggers were installed.
#
# In addition, to avoid other errors during a multi-node migration it doesn't
# set the created_at column to be non-nullable to match how the sql_model
# is defined.


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    password_table = sql.Table('password', meta, autoload=True)
    values = {'created_at': datetime.datetime.utcnow()}
    stmt = password_table.update().where(
        password_table.c.created_at == null()).values(values)
    stmt.execute()
    password_table.c.created_at.alter(nullable=False)
