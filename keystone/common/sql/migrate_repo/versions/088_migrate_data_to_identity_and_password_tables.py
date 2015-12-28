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
    con = migrate_engine.connect()

    con.execute("delete from password;")
    con.execute("delete from identity;")

    sql = "insert  into identity (identity_id, extra, enabled)"
    sql += "select id, extra, enabled from user;"
    con.execute(sql)

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
    con.execute(sql)

    con.close()


def downgrade(migrate_engine):
    pass
