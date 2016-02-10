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

from migrate import UniqueConstraint


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    user_table = sql.Table('user', meta, autoload=True)
    local_user_table = sql.Table('local_user', meta, autoload=True)
    password_table = sql.Table('local_user_password', meta, autoload=True)

    # migrate data to local_user table
    local_user_dict = []
    for row in user_table.select().execute():
        local_user_dict.append({'user_id': row['id'],
                                'domain_id': row['domain_id'],
                                'name': row['name']})
    if local_user_dict:
        local_user_table.insert().values(local_user_dict).execute()

    # migrate data to local_user_password table
    sel = (
        sql.select([user_table, local_user_table], use_labels=True)
           .select_from(user_table.join(local_user_table, user_table.c.id ==
                                        local_user_table.c.user_id))
    )
    user_rows = sel.execute()
    password_dict = []
    for row in user_rows:
        password_dict.append({'local_user_id': row['local_user_id'],
                              'password': row['user_password']})
    if password_dict:
        password_table.insert().values(password_dict).execute()

    # remove domain_id and name unique index
    if migrate_engine.name != 'sqlite':
        UniqueConstraint('domain_id', 'name', table=user_table).drop()

    # drop user columns
    user_table.c.domain_id.drop()
    user_table.c.name.drop()
    user_table.c.password.drop()
