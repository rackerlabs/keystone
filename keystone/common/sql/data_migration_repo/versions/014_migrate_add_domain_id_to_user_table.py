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

    user_table = sql.Table('user', meta, autoload=True)
    local_user_table = sql.Table('local_user', meta, autoload=True)
    nonlocal_user_table = sql.Table('nonlocal_user', meta, autoload=True)

    # update the user.domain_id from the local_user table
    local_users = list(local_user_table.select().execute())
    for local_user in local_users:
        values = {'domain_id': local_user.domain_id}
        stmt = user_table.update().where(
            sql.and_(
                user_table.c.domain_id == expression.null(),
                user_table.c.id == local_user.user_id)).values(values)
        stmt.execute()

    # update the user.domain_id from the nonlocal_user table
    nonlocal_users = list(nonlocal_user_table.select().execute())
    for nonlocal_user in nonlocal_users:
        values = {'domain_id': nonlocal_user.domain_id}
        stmt = user_table.update().where(
            sql.and_(
                user_table.c.domain_id == expression.null(),
                user_table.c.id == nonlocal_user.user_id)).values(values)
        stmt.execute()
