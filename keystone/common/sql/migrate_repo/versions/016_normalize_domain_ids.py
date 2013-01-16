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


# TDOD(henry-nash) Come back and try and find a cleaner way of
# handling these constraints - maybe by using deferred triggers.
# The method below is too prone to breakage if someone adds a
# new table that includes a foreign key
def _disable_foreign_constraints(session, migrate_engine, table_name):
    if migrate_engine.name == 'postgresql':
        if table_name == 'user':
            session.execute('ALTER TABLE user_project_membership '
                            'DISABLE TRIGGER ALL;' % table_name)
            session.execute('ALTER TABLE user_domain_metadata '
                            'DISABLE TRIGGER ALL;' % table_name)
            session.execute('ALTER TABLE credential '
                            'DISABLE TRIGGER ALL;' % table_name)
            session.execute('ALTER TABLE user_group_membership '
                            'DISABLE TRIGGER ALL;' % table_name)
        else:
            # Project Table FKs
            session.execute('ALTER TABLE user_project_membership '
                            'DISABLE TRIGGER ALL;' % table_name)
            session.execute('ALTER TABLE credential '
                            'DISABLE TRIGGER ALL;' % table_name)
    elif migrate_engine.name != 'sqlite':
        session.execute('SET foreign_key_checks = 0;')


def _enable_foreign_constraints(session, migrate_engine, table_name):
    if migrate_engine.name == 'postgresql':
        if table_name == 'user':
            session.execute('ALTER TABLE user_project_membership '
                            'ENABLE TRIGGER ALL;' % table_name)
            session.execute('ALTER TABLE user_domain_metadata '
                            'ENABLE TRIGGER ALL;' % table_name)
            session.execute('ALTER TABLE credential '
                            'ENABLE TRIGGER ALL;' % table_name)
            session.execute('ALTER TABLE user_group_membership '
                            'ENABLE TRIGGER ALL;' % table_name)
        else:
            # Project Table FKs
            session.execute('ALTER TABLE user_project_membership '
                            'ENABLE TRIGGER ALL;' % table_name)
            session.execute('ALTER TABLE credential '
                            'ENABLE TRIGGER ALL;' % table_name)
    elif migrate_engine.name != 'sqlite':
        session.execute('SET foreign_key_checks = 1;')


def upgrade_user_table(meta, migrate_engine, session):
    # We want to add the domain_id attribute to the user table.  Since
    # it is non nullable and the table may have data, easiest way is
    # a table copy. Further, in order to keep foreign key constraints
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
    # user table, with the additional domain_id column
    _disable_foreign_constraints(session, migrate_engine, 'user')
    # Be careful, since user is a reserved term in postgreql
    if migrate_engine.name == 'postgresql':
        session.execute('drop table "user";')
    else:
        session.execute('drop table user;')
    # Need to create a new metadata stream since we are going to load a
    # different version of the user table
    meta2 = sql.MetaData()
    meta2.bind = migrate_engine
    domain_table = sql.Table('domain', meta2, autoload=True)
    user_table = sql.Table(
        'user',
        meta2,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(64), unique=True, nullable=False),
        sql.Column('domain_id', sql.String(64), sql.ForeignKey('domain.id'),
                   nullable=False),
        sql.Column("password", sql.String(128)),
        sql.Column("enabled", sql.Boolean, default=True),
        sql.Column('extra', sql.Text()))
    user_table.create(migrate_engine, checkfirst=True)

    # Finally copy in the data from our temp table and then clean
    # up by deleting our temp table
    for user in session.query(temp_user_table):
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
    _enable_foreign_constraints(session, migrate_engine, 'user')
    session.execute("drop table temp_user;")


def upgrade_project_table(meta, migrate_engine, session):
    # We want to add the domain_id attribute to the project table.  Since
    # it is non nullable and the table may have data, easiest way is
    # a table copy. Further, in order to keep foreign key constraints
    # pointing at the right table, we need to be able and do a table
    # DROP then CREATE, rather than ALTERing the name of the table.

    # Fist make a copy of the project table
    temp_project_table = sql.Table(
        'temp_project',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(64), unique=True, nullable=False),
        sql.Column('extra', sql.Text()),
        sql.Column("description", sql.Text()),
        sql.Column("enabled", sql.Boolean, default=True))
    temp_project_table.create(migrate_engine, checkfirst=True)

    project_table = sql.Table('project', meta, autoload=True)
    for project in session.query(project_table):
        session.execute("insert into temp_project (id, name, extra, "
                        "description, enabled) "
                        "values ( :id, :name, :extra, "
                        ":description, :enabled);",
                        {'id': project.id,
                         'name': project.name,
                         'extra': project.extra,
                         'description': project.description,
                         'enabled': project.enabled})

    # Now switch off constraints while we drop and then re-create the
    # project table, with the additional domain_id column
    _disable_foreign_constraints(session, migrate_engine, 'project')
    session.execute("drop table project;")
    # Need to create a new metadata stream since we are going to load a
    # different version of the project table
    meta2 = sql.MetaData()
    meta2.bind = migrate_engine
    domain_table = sql.Table('domain', meta2, autoload=True)
    project_table = sql.Table(
        'project',
        meta2,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(64), unique=True, nullable=False),
        sql.Column('domain_id', sql.String(64), sql.ForeignKey('domain.id'),
                   nullable=False),
        sql.Column('description', sql.Text()),
        sql.Column("enabled", sql.Boolean, default=True),
        sql.Column('extra', sql.Text()))
    project_table.create(migrate_engine, checkfirst=True)

    # Finally copy in the data from our temp table and then clean
    # up by deleting our temp table
    for project in session.query(temp_project_table):
        session.execute("insert into project (id, name, domain_id, "
                        "description, enabled, extra) "
                        "values ( :id, :name, :domain_id, "
                        ":description, :enabled, :extra);",
                        {'id': project.id,
                         'name': project.name,
                         'domain_id': DEFAULT_DOMAIN_ID,
                         'description': project.description,
                         'enabled': project.enabled,
                         'extra': project.extra})
    _enable_foreign_constraints(session, migrate_engine, 'project')
    session.execute("drop table temp_project;")


def downgrade_user_table(meta, migrate_engine, session):
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
        # Temporary table, so no need to make it a foreign key
        sql.Column('domain_id', sql.String(64), nullable=False),
        sql.Column("password", sql.String(128)),
        sql.Column("enabled", sql.Boolean, default=True),
        sql.Column('extra', sql.Text()))
    temp_user_table.create(migrate_engine, checkfirst=True)

    user_table = sql.Table('user', meta, autoload=True)
    for user in session.query(user_table):
        session.execute("insert into temp_user (id, name, domain_id, "
                        "password, enabled, extra) "
                        "values ( :id, :name, :domain_id, "
                        ":password, :enabled, :extra);",
                        {'id': user.id,
                         'name': user.name,
                         'domain_id': user.domain_id,
                         'password': user.password,
                         'enabled': user.enabled,
                         'extra': user.extra})

    # Now switch off constraints while we drop and then re-create the
    # user table, less the columns we wanted to drop
    _disable_foreign_constraints(session, migrate_engine, 'user')
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
        sql.Column('extra', sql.Text()),
        sql.Column("password", sql.String(128)),
        sql.Column("enabled", sql.Boolean, default=True))
    user_table.create(migrate_engine, checkfirst=True)
    _enable_foreign_constraints(session, migrate_engine, 'user')

    # Finally copy in the data from our temp table and then clean
    # up by deleting our temp table
    for user in session.query(temp_user_table):
        session.execute("insert into user (id, name, extra, "
                        "password, enabled) "
                        "values ( :id, :name, :extra, "
                        ":password, :enabled);",
                        {'id': user.id,
                         'name': user.name,
                         'extra': user.extra,
                         'password': user.password,
                         'enabled': user.enabled})
    session.execute("drop table temp_user;")


def downgrade_project_table(meta, migrate_engine, session):
    # Since not all engines support dropping columns, we need to do this
    # as a table copy.  Further, in order to keep foreign key constraints
    # pointing at the right table, we need to be able and do a table
    # DROP then CREATE, rather than ALTERing the name of the table.

    # Fist make a copy of the project table
    temp_project_table = sql.Table(
        'temp_project',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(64), unique=True, nullable=False),
        # Temporary table, so no need to make it a foreign key
        sql.Column('domain_id', sql.String(64), nullable=False),
        sql.Column('description', sql.Text()),
        sql.Column("enabled", sql.Boolean, default=True),
        sql.Column('extra', sql.Text()))
    temp_project_table.create(migrate_engine, checkfirst=True)

    project_table = sql.Table('project', meta, autoload=True)
    for project in session.query(project_table):
        session.execute("insert into temp_project (id, name, domain_id, "
                        "description, enabled, extra) "
                        "values ( :id, :name, :domain_id, "
                        ":description, :enabled, :extra);",
                        {'id': project.id,
                         'name': project.name,
                         'domain_id': project.domain_id,
                         'description': project.description,
                         'enabled': project.enabled,
                         'extra': project.extra})

    # Now switch off constraints while we drop and then re-create the
    # project table, less the columns we wanted to drop
    _disable_foreign_constraints(session, migrate_engine, 'project')
    session.execute("drop table project;")
    # Need to create a new metadata stream since we are going to load a
    # different version of the project table
    meta2 = sql.MetaData()
    meta2.bind = migrate_engine
    project_table = sql.Table(
        'project',
        meta2,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(64), unique=True, nullable=False),
        sql.Column('extra', sql.Text()),
        sql.Column("description", sql.Text()),
        sql.Column("enabled", sql.Boolean, default=True))
    project_table.create(migrate_engine, checkfirst=True)
    _enable_foreign_constraints(session, migrate_engine, 'project')

    # Finally copy in the data from our temp table and then clean
    # up by deleting our temp table
    for project in session.query(temp_project_table):
        session.execute("insert into project (id, name, extra, "
                        "description, enabled) "
                        "values ( :id, :name, :extra, "
                        ":description, :enabled);",
                        {'id': project.id,
                         'name': project.name,
                         'extra': project.extra,
                         'description': project.description,
                         'enabled': project.enabled})
    session.execute("drop table temp_project;")


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    session = sessionmaker(bind=migrate_engine)()
    upgrade_user_table(meta, migrate_engine, session)
    upgrade_project_table(meta, migrate_engine, session)
    session.commit()
    session.close()


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    session = sessionmaker(bind=migrate_engine)()
    downgrade_user_table(meta, migrate_engine, session)
    downgrade_project_table(meta, migrate_engine, session)
    session.commit()
    session.close()
