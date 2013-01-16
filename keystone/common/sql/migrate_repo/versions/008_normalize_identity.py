# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
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


import sqlalchemy as sql
from sqlalchemy.orm import sessionmaker


def _disable_foreign_constraints(session, migrate_engine):
    if migrate_engine.name != "sqlite":
        session.execute("SET foreign_key_checks = 0;")


def _enable_foreign_constraints(session, migrate_engine):
    if migrate_engine.name != "sqlite":
        session.execute("SET foreign_key_checks = 1;")


def downgrade_user_table(meta, migrate_engine):
    session = sessionmaker(bind=migrate_engine)()
    # Since not all engines support dropping columns, we need to do this
    # as a table copy.  Further, in order to keep foreign key constraints
    # pointing at the right table, we need to be able and do a table
    # DROP then CREATE, rather than ALTERing the name of the table.

    # Fist make a copy of the user table
    temp_user_table = sql.Table(
        'temp_user',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(64), unique=True, nullable=False),
        sql.Column('extra', sql.Text()),
        sql.Column("password", sql.String(128)),
        sql.Column("enabled", sql.Boolean, default=True))
    temp_user_table.create(migrate_engine, checkfirst=True)

    user_table = sql.Table('user', meta, autoload=True)
    for user in session.query(user_table):
        session.execute("insert into temp_user (id, name, extra, "
                        "password, enabled) "
                        "values ( :id, :name, :extra, "
                        ":password, :enabled);",
                        {'id': user.id,
                         'name': user.name,
                         'extra': user.extra,
                         'password': user.password,
                         'enabled': user.enabled})

    # Now switch off constraints while we drop and then re-create the
    # user table, less the columns we wanted to drop
    _disable_foreign_constraints(session, migrate_engine)
    session.execute("drop table user;")
    # Need to create a new metadata stream since we are going to load a
    # different version of the user table
    meta2 = sql.MetaData()
    meta2.bind = migrate_engine
    user_table = sql.Table(
        'user',
        meta2,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(64), unique=True, nullable=False),
        sql.Column('extra', sql.Text()))
    user_table.create(migrate_engine, checkfirst=True)
    _enable_foreign_constraints(session, migrate_engine)

    # Finally copy in the data from our temp table and then clean
    # up by deleting our temp table
    for user in session.query(temp_user_table):
        session.execute("insert into user (id, name, extra) "
                        "values ( :id, :name, :extra);",
                        {'id': user.id,
                         'name': user.name,
                         'extra': user.extra})
    session.execute("drop table temp_user;")


def downgrade_tenant_table(meta, migrate_engine):
    session = sessionmaker(bind=migrate_engine)()
    # Since not all engines support dropping columns, we need to do this
    # as a table copy.  Further, in order to keep foreign key constraints
    # pointing at the right table, we need to be able and do a table
    # DROP then CREATE, rather than ALTERing the name of the table.

    # Fist make a copy of the tenant table
    temp_tenant_table = sql.Table(
        'temp_tenant',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(64), unique=True, nullable=False),
        sql.Column('extra', sql.Text()),
        sql.Column("description", sql.Text()),
        sql.Column("enabled", sql.Boolean, default=True))
    temp_tenant_table.create(migrate_engine, checkfirst=True)

    tenant_table = sql.Table('tenant', meta, autoload=True)
    for tenant in session.query(tenant_table):
        session.execute("insert into temp_tenant (id, name, extra, "
                        "description, enabled) "
                        "values ( :id, :name, :extra, "
                        ":description, :enabled);",
                        {'id': tenant.id,
                         'name': tenant.name,
                         'extra': tenant.extra,
                         'description': tenant.description,
                         'enabled': tenant.enabled})

    # Now switch off constraints while we drop and then re-create the
    # tenant table, less the columns we wanted to drop
    _disable_foreign_constraints(session, migrate_engine)
    session.execute("drop table tenant;")
    # Need to create a new metadata stream since we are going to load a
    # different version of the tenant table
    meta2 = sql.MetaData()
    meta2.bind = migrate_engine
    tenant_table = sql.Table(
        'tenant',
        meta2,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(64), unique=True, nullable=False),
        sql.Column('extra', sql.Text()))
    tenant_table.create(migrate_engine, checkfirst=True)
    _enable_foreign_constraints(session, migrate_engine)

    # Finally copy in the data from our temp table and then clean
    # up by deleting our temp table
    for tenant in session.query(temp_tenant_table):
        session.execute("insert into tenant (id, name, extra) "
                        "values ( :id, :name, :extra);",
                        {'id': tenant.id,
                         'name': tenant.name,
                         'extra': tenant.extra})
    session.execute("drop table temp_tenant;")


def upgrade_user_table(meta, migrate_engine):
    user_table = sql.Table('user', meta, autoload=True)
    user_table.create_column(sql.Column("password", sql.String(128)))
    user_table.create_column(sql.Column("enabled", sql.Boolean,
                             default=True))


def upgrade_tenant_table(meta, migrate_engine):
    tenant_table = sql.Table('tenant', meta, autoload=True)
    tenant_table.create_column(sql.Column("description", sql.Text()))
    tenant_table.create_column(sql.Column("enabled", sql.Boolean))


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    upgrade_user_table(meta, migrate_engine)
    upgrade_tenant_table(meta, migrate_engine)


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    downgrade_user_table(meta, migrate_engine)
    downgrade_tenant_table(meta, migrate_engine)
