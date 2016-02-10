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

import uuid

import sqlalchemy as sql


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    identity_table = sql.Table('identity', meta, autoload=True)
    user_table = sql.Table('user', meta, autoload=True)
    password_table = sql.Table('password', meta, autoload=True)

    # migrate data - user table
    sel = (
        identity_table.select().where(identity_table.c.id.notin_(
            sql.select([user_table.c.identity_id])))
    )
    rows = sel.execute()
    user_dict = []
    for row in rows:
        user_dict.append({'id': uuid.uuid4().hex,
                          'identity_id': row['id'],
                          'domain_id': row['domain_id'],
                          'name': row['name']})
    if user_dict:
        user_table.insert().values(user_dict).execute()

    # migrate data - password table
    sel = (
        sql.select([identity_table, user_table], use_labels=True)
           .select_from(identity_table.join(user_table, identity_table.c.id ==
                                            user_table.c.identity_id))
           .where(user_table.c.id.notin_(
               sql.select([password_table.c.user_id])))
    )
    rows = sel.execute()
    password_dict = []
    for row in rows:
        password_dict.append({'id': row['identity_id'],
                              'user_id': row['user_id'],
                              'password': row['identity_password']})
    if password_dict:
        password_table.insert().values(password_dict).execute()
