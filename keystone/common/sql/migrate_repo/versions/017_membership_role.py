import json
import sqlalchemy as sql
from sqlalchemy import orm

import uuid
from keystone import config
from keystone import exception


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    user_table = sql.Table('user', meta, autoload=True)
    role_table = sql.Table('role', meta, autoload=True)
    project_table = sql.Table('project', meta, autoload=True)

    user_project_role_table = sql.Table(
        'user_project_metadata',
        meta,
        sql.Column('user_id',
                   sql.String(64),
                   sql.ForeignKey('user.id'),
                   primary_key=True),
        sql.Column('project_id',
                   sql.String(64),
                   sql.ForeignKey('project.id'),
                   primary_key=True),
        sql.Column('data', sql.Text()))
    user_project_role_table.create(migrate_engine, checkfirst=True)

    conn = migrate_engine.connect()
    conn.execute(role_table.insert(),
                 id=config.CONF.member_role_id,
                 name="Member_of_Project",
                 extra=json.dumps({'description':
                                   'Default role for project membership'}))

    user_project_membership_table = sql.Table('user_project_membership',
                                              meta, autoload=True)
    session = sql.orm.sessionmaker(bind=migrate_engine)()
    for membership in session.query(user_project_membership_table):
        data = {'roles': [config.CONF.member_role_id]}
        ins = user_project_role_table.insert().values(
            user_id=membership.user_id,
            project_id=membership.project_id,
            data=json.dumps(data))
        conn.execute(ins)
    user_project_membership_table.drop()


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    user_table = sql.Table('user', meta, autoload=True)
    project_table = sql.Table('project', meta, autoload=True)

    user_project_membership_table = sql.Table(
        'user_project_membership',
        meta,
        sql.Column(
            'user_id',
            sql.String(64),
            sql.ForeignKey('user.id'),
            primary_key=True),
        sql.Column(
            'project_id',
            sql.String(64),
            sql.ForeignKey('project.id'),
            primary_key=True))
    user_project_membership_table.create(migrate_engine, checkfirst=True)

    user_project_role_table = sql.Table(
        'user_project_metadata',
        meta,
        autoload=True)

    session = sql.orm.sessionmaker(bind=migrate_engine)()
    for membership in session.query(user_project_role_table):
        if 'roles' in membership:
            roles = membership['roles']
            if config.CONF.member_role_id in roles:
                ins = user_project_membership_table.insert().\
                    values(user_id=membership.user_id,
                           project_id=membership.project_id)

    role_table = sql.Table('role', meta, autoload=True)
    conn = migrate_engine.connect()
    user_project_role_table = sql.Table(
        'user_project_membership', meta, autoload=True)

    role_table = sql.Table('role', meta, autoload=True)
    conn.execute(role_table.delete().where(role_table.c.id ==
                                           config.CONF.member_role_id))
