# vim: tabstop=4 shiftwidth=4 softtabstop=4

"""Export data from Nova database and import through Identity Service"""

import uuid

import sqlalchemy

from keystone.contrib.ec2.backends import sql as ec2_sql
from keystone.identity.backends import sql as identity_sql


def export_auth(db_string):
    db = sqlalchemy.create_engine(db_string)
    users, ec2_credentials = _export_users(db)
    tenants = _export_tenants(db)
    user_tenant_list = _export_user_tenant_list(db)
    roles, role_user_tenant_list = _export_roles(db)

    migration_data = {
        'users': users,
        'ec2_credentials': ec2_credentials,
        'tenants': tenants,
        'roles': roles,
        'user_tenant_list': user_tenant_list,
        'role_user_tenant_list': role_user_tenant_list,
    }
    return migration_data


def _dump_raw(db, table_name, column_names):
    query = db.execute("select * from %s where deleted=0" % table_name)
    table_data = []
    for row in query.fetchall():
        entry = {}
        for column_name in column_names:
            entry[column_name] = getattr(row, column_name, None)
        table_data.append(entry)

    return table_data


def _export_users(db):
    user_columns = ('id', 'name', 'access_key', 'secret_key')
    users = _dump_raw(db, 'users', user_columns)
    ec2_credentials = []
    for user in users:
        ec2_cred = {
            'user_id': user['id'],
            'access_key': user.pop('access_key'),
            'secret_key': user.pop('secret_key'),
        }
        ec2_credentials.append(ec2_cred)
    return users, ec2_credentials


def _export_tenants(db):
    tenant_columns = ('id', 'name', 'description')
    tenants = _dump_raw(db, 'projects', tenant_columns)
    return tenants


def _export_user_tenant_list(db):
    ut_map_columns = ('user_id', 'project_id')
    ut_map = _dump_raw(db, 'user_project_association', ut_map_columns)
    for rel in ut_map:
        rel['tenant_id'] = rel.pop('project_id')
    return ut_map


def _export_roles(db):
    role_columns = ('role', 'user_id', 'project_id')
    tablename = 'user_project_role_association'
    role_map = _dump_raw(db, tablename, role_columns)
    roles = []
    for row in role_map:
        if row['role'] not in roles:
            roles.append(row['role'])
        row['tenant_id'] = row.pop('project_id')
    return roles, role_map


def import_auth(data):
    identity_api = identity_sql.Identity()
    tenant_map = _create_tenants(identity_api, data['tenants'])
    user_map = _create_users(identity_api, data['users'])
    _create_memberships(identity_api, data['user_tenant_list'],
                        user_map, tenant_map)
    role_map = _create_roles(identity_api, data['roles'])
    _assign_roles(identity_api, data['role_user_tenant_list'],
                  role_map, user_map, tenant_map)

    ec2_api = ec2_sql.Ec2()
    ec2_creds = data['ec2_credentials']
    _create_ec2_creds(ec2_api, identity_api, ec2_creds, user_map)


def _generate_uuid():
    return uuid.uuid4().hex


def _create_tenants(api, tenants):
    tenant_map = {}
    for tenant in tenants:
        tenant_dict = {
            'id': uuid.uuid4().hex,
            'name': tenant.get('name') or tenant.get('id'),
            'description': tenant['description'],
            'enabled': True,
        }
        tenant_map[tenant['id']] = tenant_dict['id']
        print 'Create tenant %s' % tenant_dict
        api.create_tenant(tenant_dict['id'], tenant_dict)
    return tenant_map


def _create_users(api, users):
    user_map = {}
    for user in users:
        user_dict = {
            'id': uuid.uuid4().hex,
            'name': user['id'],
            'email': '',
            'password': None,
            'enabled': True,
        }
        user_map[user['id']] = user_dict['id']
        print 'Create user %s' % user_dict
        api.create_user(user_dict['id'], user_dict)
    return user_map


def _create_memberships(api, memberships, user_map, tenant_map):
    for membership in memberships:
        user_id = user_map[membership['user_id']]
        tenant_id = tenant_map[membership['tenant_id']]
        print 'Add user %s to tenant %s' % (user_id, tenant_id)
        api.add_user_to_tenant(tenant_id, user_id)


def _create_roles(api, roles):
    role_map = {}
    for role in roles:
        role_dict = {
            'id': _generate_uuid(),
            'name': role,
        }
        role_map[role] = role_dict['id']
        print 'Create role %s' % role_dict
        api.create_role(role_dict['id'], role_dict)
    return role_map


def _assign_roles(api, assignments, role_map, user_map, tenant_map):
    for assignment in assignments:
        role_id = role_map[assignment['role']]
        user_id = user_map[assignment['user_id']]
        tenant_id = tenant_map[assignment['tenant_id']]
        print 'Assign role %s to user %s on tenant %s' % (role_id, user_id, tenant_id)
        api.add_role_to_user_and_tenant(user_id, tenant_id, role_id)


def _create_ec2_creds(ec2_api, identity_api, ec2_creds, user_map):
    for ec2_cred in ec2_creds:
        user_id = user_map[ec2_cred['user_id']]
        for tenant_id in identity_api.get_tenants_for_user(user_id):
            cred_dict = {
                'access': '%s:%s' % (tenant_id, ec2_cred['access_key']),
                'secret': ec2_cred['secret_key'],
                'user_id': user_id,
                'tenant_id': tenant_id,
            }
            print 'Creating ec2 cred for user %s and tenant %s' % (user_id, tenant_id)
            ec2_api.create_credential(None, cred_dict)

