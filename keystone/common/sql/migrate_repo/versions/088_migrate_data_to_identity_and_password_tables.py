# Copyright 2014 IBM Corp.
#
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

    user_table = sql.Table('user', meta, autoload=True)
    identity_table = sql.Table('identity', meta, autoload=True)
    password_table = sql.Table('password', meta, autoload=True)

    # insert identities
    identity_table.delete().execute()
    sel = sql.select([user_table.c.id, user_table.c.extra,
                      user_table.c.enabled, user_table.c.default_project_id])
    ins = identity_table.insert().from_select(['identity_id',
                                               'extra',
                                               'enabled',
                                               'default_project_id'], sel)
    ins.execute()

    # insert passwords
    users = user_table.select().execute()
    password_records = []
    for user in users:
        password_records.append({'password_id': uuid.uuid4().hex,
                                 'identity_id': user['id'],
                                 'user_name': user['name'],
                                 'namespace': user['domain_id'],
                                 'password': user['password']})
    if password_records:
        password_table.insert().values(password_records).execute()


def downgrade(migrate_engine):
    pass
