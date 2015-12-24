import sqlalchemy as mysql

from keystone.common.sql import migration_helpers


def upgrade(migrate_engine):
    meta = mysql.MetaData()
    meta.bind = migrate_engine
    con = migrate_engine.connect()

    con.execute("delete from password;")
    con.execute("delete from identity;")

    sql = "insert  into identity (identity_id, extra, enabled)"
    sql += "select id, extra, enabled from user;"
    con.execute(sql)

    sql = "insert into password (password_id, identity_id, user_name,"
    sql += "namespace)"
    sql += "select uuid(), id, name, domain_id, password from user;"
    con.execute(sql)

    con.close()
