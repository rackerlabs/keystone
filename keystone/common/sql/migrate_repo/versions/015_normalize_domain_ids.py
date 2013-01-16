# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
# Copyright 2013 IBM
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
from keystone import config


CONF = config.CONF
DEFAULT_DOMAIN_ID = CONF['identity']['default_domain_id']


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    meta = sql.MetaData()
    meta.bind = migrate_engine

    maker = sessionmaker(bind=migrate_engine)
    session = maker()
    # First add the domain_id attribute to the user table.  We have to
    # do this as a table copy since domain_id is non nullable
    domain_table = sql.Table('domain', meta, autoload=True)
    session.execute("ALTER TABLE user RENAME TO orig_user;")
    user_table = sql.Table(
        'user',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(64), unique=True, nullable=False),
        sql.Column('domain_id', sql.String(64), sql.ForeignKey('domain.id'),
                   nullable=False),
        sql.Column("password", sql.String(128)),
        sql.Column("enabled", sql.Boolean, default=True),
        sql.Column('extra', sql.Text()))
    user_table.create(migrate_engine, checkfirst=True)

    orig_user_table = sql.Table('orig_user', meta, autoload=True)
    for user in session.query(orig_user_table):
        session.execute("insert into user (id, name, domain_id, "
                        "password, enabled, extra) "
                        "values ( :id, :name, :domain_id, "
                        ":password, :enabled, :extra);",
                        {'id': user.id,
                         'name': user.name,
                         'domain_id': DEFAULT_DOMAIN_ID,
                         'password': user.password,
                         'enabled': user.enabled,
                         'extra': user.extra})
    session.execute("drop table orig_user;")

    # Now do the same for tenants table
    session.execute("ALTER TABLE tenant RENAME TO orig_tenant1;")
    tenant_table = sql.Table(
        'tenant',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(64), unique=True, nullable=False),
        sql.Column('domain_id', sql.String(64), sql.ForeignKey('domain.id'),
                   nullable=False),
        sql.Column('description', sql.Text()),
        sql.Column("enabled", sql.Boolean, default=True),
        sql.Column('extra', sql.Text()))
    tenant_table.create(migrate_engine, checkfirst=True)

    orig_tenant_table = sql.Table('orig_tenant1', meta, autoload=True)
    for tenant in session.query(orig_tenant_table):
        session.execute("insert into tenant (id, name, domain_id, "
                        "description, enabled, extra) "
                        "values ( :id, :name, :domain_id, "
                        ":description, :enabled, :extra);",
                        {'id': tenant.id,
                         'name': tenant.name,
                         'domain_id': DEFAULT_DOMAIN_ID,
                         'description': tenant.description,
                         'enabled': tenant.enabled,
                         'extra': tenant.extra})
    session.execute("drop table orig_tenant1;")


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    maker = sessionmaker(bind=migrate_engine)

    session = maker()
    # Don't just try and drop the domain_id, for two reasons:
    # - not all DBs support that
    # - need to make sure the column order is as it was
    session.execute("ALTER TABLE user RENAME TO orig_user;")
    user_table = sql.Table(
        'user',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(64), unique=True, nullable=False),
        sql.Column('extra', sql.Text()),
        sql.Column("password", sql.String(128)),
        sql.Column("enabled", sql.Boolean, default=True))
    user_table.create(migrate_engine, checkfirst=True)

    orig_user_table = sql.Table('orig_user', meta, autoload=True)
    for user in session.query(orig_user_table):
        session.execute("insert into user (id, name, extra, "
                        "password, enabled) "
                        "values ( :id, :name, :extra, "
                        ":password, :enabled);",
                        {'id': user.id,
                         'name': user.name,
                         'password': user.password,
                         'enabled': user.enabled,
                         'extra': user.extra})
    session.execute("drop table orig_user;")

    # Now the same for tenants
    session.execute("ALTER TABLE tenant RENAME TO orig_tenant1;")
    tenant_table = sql.Table(
        'tenant',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(64), unique=True, nullable=False),
        sql.Column('extra', sql.Text()),
        sql.Column('description', sql.Text()),
        sql.Column('enabled', sql.Boolean, default=True))
    tenant_table.create(migrate_engine, checkfirst=True)

    orig_tenant_table = sql.Table('orig_tenant1', meta, autoload=True)
    for tenant in session.query(orig_tenant_table):
        session.execute("insert into tenant (id, name, extra, "
                        "description, enabled) "
                        "values ( :id, :name, :extra, "
                        ":description, :enabled);",
                        {'id': tenant.id,
                         'name': tenant.name,
                         'extra': tenant.extra,
                         'description': tenant.description,
                         'enabled': tenant.enabled})
    session.execute("drop table orig_tenant1;")
