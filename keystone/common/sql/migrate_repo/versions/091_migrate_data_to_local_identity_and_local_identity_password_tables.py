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
    local_table = sql.Table('local_identity', meta, autoload=True)
    password_table = sql.Table('local_identity_password', meta, autoload=True)

    # migrate data - local_identity table
    sel = (
        identity_table.select().where(identity_table.c.id.notin_(
            sql.select([local_table.c.id])))
    )
    rows = sel.execute()
    local_identity_dict = []
    for row in rows:
        local_identity_dict.append({'id': row['id'],
                                    'domain_id': row['domain_id'],
                                    'name': row['name']})
    if local_identity_dict:
        local_table.insert().values(local_identity_dict).execute()

    # migrate data - local_identity_password table
    sel = (
        identity_table.select().where(identity_table.c.id.notin_(
            sql.select([password_table.c.local_identity_id])))
    )
    rows = sel.execute()
    password_dict = []
    for row in rows:
        password_dict.append({'local_identity_id': row['id'],
                              'password': row['password']})
    if password_dict:
        password_table.insert().values(password_dict).execute()
