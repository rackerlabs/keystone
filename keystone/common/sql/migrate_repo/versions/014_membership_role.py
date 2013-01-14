import json
import sqlalchemy as sql
from sqlalchemy import orm

import uuid
from keystone import exception


member_role_uuid ="9fe2ff9ee4384b1894a90878d3e92bab"

def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    user_table = sql.Table('user', meta, autoload=True)
    role_table = sql.Table('role', meta, autoload=True)
    project_table = sql.Table('tenant', meta, autoload=True)

    project_table.rename('project')

    user_project_role_table = sql.Table(
        'user_project_role',
        meta,
        sql.Column('user_id', sql.String(64), sql.ForeignKey('user.id'), primary_key=True ),
        sql.Column('project_id', sql.String(64), sql.ForeignKey('tenant.id'), primary_key=True ),
        sql.Column('role_id', sql.String(64), sql.ForeignKey('role.id'), primary_key=True ),
        sql.Column('data', sql.Text()))
    user_project_role_table.create(migrate_engine, checkfirst=True)

    conn = migrate_engine.connect()
    conn.execute(role_table.insert(),
                 id=member_role_uuid,
                 name="Member_of_Project",
                 description='Default Role for Project Membership',
                 extra=json.dumps({'description': 
                                   'Default Role for Project Membership'})
                 )

    user_tenant_membership_table = sql.Table('user_tenant_membership', meta, autoload=True)
    maker = sql.orm.sessionmaker(bind=migrate_engine)
    session = maker()
    for membership in session.query(user_tenant_membership_table):
        ins = user_project_role_table.insert().values(user_id=membership.user_id,
                                                       project_id=membership.tenant_id,
                                                       role_id=member_role_uuid)
        conn.execute(ins)
    user_tenant_membership_table.drop()

def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    user_table = sql.Table('user', meta, autoload=True)
    tenant_table = sql.Table('tenant', meta, autoload=True)

    user_tenant_membership_table = sql.Table(
        'user_tenant_membership',
        meta,
        sql.Column(
            'user_id',
            sql.String(64),
            sql.ForeignKey('user.id'),
            primary_key=True),
        sql.Column(
            'tenant_id',
            sql.String(64),
            sql.ForeignKey('tenant.id'),
            primary_key=True))
    user_tenant_membership_table.create(migrate_engine, checkfirst=True)

    user_project_role_table = sql.Table(
        'user_project_role',
        meta,
        autoload=True)

    maker = sql.orm.sessionmaker(bind=migrate_engine)
    session = maker()
    for membership in session.query(user_project_role_table).filter("role_id='%s'" % member_role_uuid):
        ins = user_tenant_membership_table.insert().values(user_id=membership.user_id,
                                                       tenant_id=membership.project_id,
                                                       role_id=member_role_uuid)

    role_table = sql.Table('role', meta, autoload=True)
    conn = migrate_engine.connect()
    user_project_role_table = sql.Table(
        'user_project_role',meta, autoload=True)
    user_project_role_table.drop()

    conn.execute(role_table.delete().where(role_table.c.id  == member_role_uuid))
