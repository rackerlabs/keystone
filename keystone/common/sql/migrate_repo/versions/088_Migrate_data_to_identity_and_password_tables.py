import sqlalchemy as mysql

from keystone.common.sql import migration_helpers


def upgrade(migrate_engine):
    meta = mysql.MetaData()
    meta.bind = migrate_engine
    con = migrate_engine.connect()

    con.execute("delete from password;")
    con.execute("delete from identity;")

    sql = "insert  into identity (identity_id, extra, enabled)"
    sql += "    select id, extra, enabled from user;"
    con.execute(sql)

    sql = "insert into password ("
    sql += "    password_id, identity_id, user_name, namespace,"
    sql += "    password, expires_at)"
    sql += "    select uuid(), id, name, domain_id, password,"
    sql += "        (NOW() + INTERVAL 365 DAY) from user;"
    con.execute(sql)

    con.close()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pass
