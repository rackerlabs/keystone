# pylint: disable=C0103


import sqlalchemy
import migrate


meta = sqlalchemy.MetaData()

user = {}
user['id'] = sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True,
        autoincrement=True)
user['name'] = sqlalchemy.Column('name', sqlalchemy.String(255), unique=True)
user['password'] = sqlalchemy.Column('password', sqlalchemy.String(255))
user['email'] = sqlalchemy.Column('email', sqlalchemy.String(255))
user['enabled'] = sqlalchemy.Column('enabled', sqlalchemy.Integer)
column_tenant_id = sqlalchemy.Column('tenant_id', sqlalchemy.Integer)
user['tenant_id'] = column_tenant_id
users = sqlalchemy.Table('users', meta, *user.values())

role = {}
role['id'] = sqlalchemy.Column('id', sqlalchemy.Integer,
        primary_key=True, autoincrement=True)
role['name'] = sqlalchemy.Column('name', sqlalchemy.String(255))
role['desc'] = sqlalchemy.Column('desc', sqlalchemy.String(255))
role['service_id'] = sqlalchemy.Column('service_id', sqlalchemy.Integer)
roles = sqlalchemy.Table('roles', meta, *role.values())

user_role = {}
user_role['id'] = sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True)
user_role['user_id'] = sqlalchemy.Column('user_id', sqlalchemy.Integer)
user_role['role_id'] = sqlalchemy.Column('role_id', sqlalchemy.Integer)
user_role['tenant_id'] = sqlalchemy.Column('tenant_id', sqlalchemy.Integer)
user_roles = sqlalchemy.Table('user_roles', meta, *user_role.values())


def upgrade(migrate_engine):
    """
    Takes default tenants out of user table.
    Existing default tenants become a role relationship.
    """
    meta.bind = migrate_engine
    droles = roles.select(whereclause="name = 'Member'").limit(1).execute()
    if not droles:
        roles.insert({'name': 'Member', 'desc':\
            'Role to manage tenant memberships.'}).execute()
        droles = roles.select(whereclause="name = 'Member'").limit(1).execute()
    for drole in droles:
        dusers = users.select("tenant_id is not null").execute()
        inserts = []
        for duser in dusers:
            inserts.append(user_roles.insert(
                {'user_id': duser.id, 'role_id': drole.id,
                 'tenant_id': duser.tenant_id}))
        #Outside of for loop to handle sqlite connection weird issues.
        for item in inserts:
            item.execute()
    migrate.drop_column(column_tenant_id, users)


def downgrade(migrate_engine):
    """
    Brings back default tenant.
    """
    meta.bind = migrate_engine
    migrate.create_column(column_tenant_id, users)
    droles = roles.select(whereclause="name = 'Member'").limit(1).execute()
    for drole in droles:
        drole_refs = user_roles.select(whereclause="role_id="
            + str(drole.id) + " ").execute()
        updates = []
        deletes = []
        for drole_ref in drole_refs:
            updates.append(users.update(
                whereclause="id=" + str(drole_ref.user_id),
                values={'tenant_id': drole_ref.tenant_id}))
            deletes.append(user_roles.delete(id=drole_ref.id))
        #Outside of for loop to handle sqlite connection weird issues.
        for item in updates:
            item.execute()
        for item in deletes:
            item.execute()
