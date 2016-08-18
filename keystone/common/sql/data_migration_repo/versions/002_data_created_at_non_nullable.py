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
import sqlalchemy.sql.expression as expression


# Migration 105 clean-up.
# In a multi-node migration, this could result in some rows left without
# the create_at value set to the current date. Despite installing triggers
# in the expand phase to fix this, given that original migration was back
# in the legacy repo, there is still a chance that some rows may still
# remaining with the created_at value unset. Hence we do a last check here to
# set any such rows to the current date.


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    password_table = sql.Table('password', meta, autoload=True)
    values = {'created_at': datetime.datetime.utcnow()}
    stmt = password_table.update().where(
        password_table.c.created_at == expression.null()).values(values)
    stmt.execute()
