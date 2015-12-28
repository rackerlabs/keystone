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

import sqlalchemy as mysql
import uuid


def upgrade(migrate_engine):
    meta = mysql.MetaData()
    meta.bind = migrate_engine

    user_table = mysql.Table('user', meta, autoload=True)
    identity_table = mysql.Table('identity', meta, autoload=True)

    # insert identities
    identity_table.delete().execute()
    sel = mysql.select([user_table.c.id, user_table.c.extra,
                        user_table.c.enabled])
    ins = identity_table.insert().from_select(['identity_id', 'extra',
                                               'enabled'], sel)
    ins.execute()

    # insert passwords
    con = migrate_engine.connect()
    users = con.execute("select id, name, domain_id, password from user;")
    sql = ""
    for user in users:
        sql += "insert into password"
        sql += "(password_id,"
        sql += "identity_id,"
        sql += "user_name,"
        sql += "namespace,"
        sql += "password)"
        sql += "values"
        sql += "('" + uuid.uuid4().hex + "',"
        sql += "'" + user["id"] + "',"
        sql += "'" + user["name"] + "',"
        sql += "'" + user["domain_id"] + "',"
        sql += "'" + user["password"] + "');" + "\n"
    if sql:
        con.execute(sql)
    con.close()


def downgrade(migrate_engine):
    pass
