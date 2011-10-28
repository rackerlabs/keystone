from sqlalchemy import *
from migrate import *

meta = MetaData()


# services

service = {}
service['id'] = Column('id', Integer, primary_key=True, autoincrement=True)
service['name'] = Column('name', String(255), unique=True)
service['type'] = Column('type', String(255))
service['desc'] = Column('desc', String(255))
services = Table('services', meta, *service.values())

UniqueConstraint(service['name'])


# roles

role = {}
role['id'] = Column('id', Integer, primary_key=True, autoincrement=True)
role['name'] = Column('name', String(255))
role['desc'] = Column('desc', String(255))
role['service_id'] = Column('service_id', Integer)
roles = Table('roles', meta, *role.values())

UniqueConstraint(role['name'], role['service_id'])

ForeignKeyConstraint(
    [role['service_id']],
    [service['id']])


# tenants

tenant = {}
tenant['id'] = Column('id', Integer, primary_key=True, autoincrement=True)
tenant['name'] = Column('name', String(255), unique=True)
tenant['desc'] = Column('desc', String(255))
tenant['enabled'] = Column('enabled', Integer)
tenants = Table('tenants', meta, *tenant.values())

UniqueConstraint(tenant['name'])


# users

user = {}
user['id'] = Column('id', Integer, primary_key=True, autoincrement=True)
user['name'] = Column('name', String(255), unique=True)
user['password'] = Column('password', String(255))
user['email'] = Column('email', String(255))
user['enabled'] = Column('enabled', Integer)
user['tenant_id'] = Column('tenant_id', Integer)
users = Table('users', meta, *user.values())

UniqueConstraint(user['name'])

ForeignKeyConstraint(
    [user['tenant_id']],
    [tenant['id']])


# credentials

credential = {}
credential['id'] = Column('id', Integer, primary_key=True, autoincrement=True)
credential['user_id'] = Column('user_id', Integer)
credential['tenant_id'] = Column('tenant_id', Integer, nullable=True)
credential['type'] = Column('type', String(20))
credential['key'] = Column('key', String(255))
credential['secret'] = Column('secret', String(255))
credentials = Table('credentials', meta, *credential.values())

ForeignKeyConstraint(
    [credential['user_id']],
    [user['id']])
ForeignKeyConstraint(
    [credential['tenant_id']],
    [tenant['id']])


# tokens

token = {}
token['id'] = Column('id', String(255), primary_key=True, unique=True)
token['user_id'] = Column('user_id', Integer)
token['tenant_id'] = Column('tenant_id', Integer)
token['expires'] = Column('expires', DateTime)
tokens = Table('tokens', meta, *token.values())


# endpoint_templates

endpoint_template = {}
endpoint_template['id'] = Column('id', Integer, primary_key=True)
endpoint_template['region'] = Column('region', String(255))
endpoint_template['service_id'] = Column('service_id', Integer)
endpoint_template['public_url'] = Column('public_url', String(2000))
endpoint_template['admin_url'] = Column('admin_url', String(2000))
endpoint_template['internal_url'] = Column('internal_url', String(2000))
endpoint_template['enabled'] = Column('enabled', Boolean)
endpoint_template['is_global'] = Column('is_global', Boolean)
endpoint_template['version_id'] = Column('version_id', String(20))
endpoint_template['version_list'] = Column('version_list', String(2000))
endpoint_template['version_info'] = Column('version_info', String(500))
endpoint_templates = Table('endpoint_templates', meta, *endpoint_template.values())

ForeignKeyConstraint(
    [endpoint_template['service_id']], [service['id']])


# endpoints

endpoint = {}
endpoint['id'] = Column('id', Integer, primary_key=True)
endpoint['tenant_id'] = Column('tenant_id', Integer)
endpoint['endpoint_template_id'] = Column('endpoint_template_id', Integer)
endpoints = Table('endpoints', meta, *endpoint.values())

UniqueConstraint(
    endpoint['endpoint_template_id'], endpoint['tenant_id'])

ForeignKeyConstraint(
    [endpoint['endpoint_template_id']],
    [endpoint_template['id']])


# user_roles

user_role = {}
user_role['id'] = Column('id', Integer, primary_key = True)
user_role['user_id'] = Column('user_id', Integer)
user_role['role_id'] = Column('role_id', Integer)
user_role['tenant_id'] = Column('tenant_id', Integer)
user_roles = Table('user_roles', meta, *user_role.values())

UniqueConstraint(
    user_role['user_id'], user_role['role_id'], user_role['tenant_id'])

ForeignKeyConstraint(
    [user_role['user_id']],
    [user['id']])
ForeignKeyConstraint(
    [user_role['role_id']],
    [role['id']])
ForeignKeyConstraint(
    [user_role['tenant_id']],
    [tenant['id']])


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    user_roles.create()
    endpoints.create()
    roles.create()
    services.create()
    tenants.create()
    users.create()
    credentials.create()
    tokens.create()
    endpoint_templates.create()


def downgrade(migrate_engine):
    meta.bind = migrate_engine

    user_roles.drop()
    endpoints.drop()
    roles.drop()
    services.drop()
    tenants.drop()
    users.drop()
    credentials.drop()
    tokens.drop()
    endpoint_templates.drop()
