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
import sqlalchemy.sql.expression as expression


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    registered_limit_table = sql.Table('registered_limit', meta, autoload=True)
    registered_limits = list(registered_limit_table.select().where(
        registered_limit_table.c.registered_limit_id == expression.null()
    ).execute())
    for registered_limit in registered_limits:
        values = {'registered_limit_id': registered_limit.id}
        registered_limit_table.update().where(
            registered_limit_table.c.id == registered_limit.id
        ).values(values).execute()

    limit_table = sql.Table('limit', meta, autoload=True)
    limits = list(limit_table.select().where(
        limit_table.c.limit_id == expression.null()
    ).execute())
    for limit in limits:
        values = {'registered_limit_id': limit.id}
        registered_limit_table.update().where(limit_table.c.id == limit.id
                                              ).values(values).execute()
