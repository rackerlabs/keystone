# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
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

import json
import uuid

import sqlalchemy as sql

USER_PROJECT_TABLE = 'user_project_metadata'
GROUP_PROJECT_TABLE = 'group_project_metadata'
USER_DOMAIN_TABLE = 'user_domain_metadata'
GROUP_DOMAIN_TABLE = 'group_domain_metadata'

GRANT_TABLES = [USER_PROJECT_TABLE, USER_DOMAIN_TABLE,
                GROUP_PROJECT_TABLE, GROUP_DOMAIN_TABLE]

USER_PROJECT_TYPE = 1
GROUP_PROJECT_TYPE = 2
USER_DOMAIN_TYPE = 3
GROUP_DOMAIN_TYPE = 4


def migrate_grant_table(meta, migrate_engine, session, table_name):

    def extract_actor_and_target(table_name, composite_grant):
        if table_name == USER_PROJECT_TABLE:
            return {'type': USER_PROJECT_TYPE,
                    'actor_id': composite_grant.user_id,
                    'target_id': composite_grant.project_id}
        elif table_name == GROUP_PROJECT_TABLE:
            return {'type': GROUP_PROJECT_TYPE,
                    'actor_id': composite_grant.group_id,
                    'target_id': composite_grant.project_id}
        elif table_name == USER_DOMAIN_TABLE:
            return {'type': USER_DOMAIN_TYPE,
                    'actor_id': composite_grant.user_id,
                    'target_id': composite_grant.domain_id}
        else:
            return {'type': GROUP_DOMAIN_TYPE,
                    'actor_id': composite_grant.group_id,
                    'target_id': composite_grant.domain_id}

    # Make each role in the list of each entry a separate assignment
    def grant_to_grant_dict_list(table_name, composite_grant):
        json_metadata = json.loads(composite_grant.data)
        role_dict_list = []
        if 'roles' in json_metadata:
            for x in json_metadata['roles']:
                if x.get('id') is None:
                    # Looks like an invalid role, drop it
                    break
                grant = extract_actor_and_target(table_name, composite_grant)
                grant['role_id'] = x.get('id')
                grant['inherited'] = False
                if x.get('inherited_to') == 'projects':
                    grant['inherited'] = True
                role_dict_list.append(grant)
        return role_dict_list

    upgrade_table = sql.Table(table_name, meta, autoload=True)
    assignment_table = sql.Table('assignment', meta, autoload=True)
    for grant in session.query(upgrade_table).all():
        for grant_role in grant_to_grant_dict_list(table_name, grant):
            new_entry = assignment_table.insert().values(
                id=uuid.uuid4().hex,
                type=grant_role['type'],
                actor_id=grant_role['actor_id'],
                target_id=grant_role['target_id'],
                role_id=grant_role['role_id'],
                inherited=grant_role['inherited'])
            migrate_engine.execute(new_entry)


def downgrade_assignment_table(meta, migrate_engine):

    def add_to_dict_list(metadata, assignment_row):
        """Update a metadata dict list with the role.

        For the assignment row supplied, we need to append the role_id into
        the metadata list of dicts.  If the row is inherited, then we mark
        it so in the dict we append.

        """
        new_entry = {'id': assignment_row.role_id}
        if assignment_row.inherited and (
                assignment_row.type == USER_DOMAIN_TYPE or
                assignment_row.type == GROUP_DOMAIN_TYPE):
            new_entry['inherited_to'] = 'projects'

        if metadata is not None:
            json_metadata = json.loads(metadata)
        else:
            json_metadata = {}

        if json_metadata.get('roles') is None:
            json_metadata['roles'] = []

        json_metadata['roles'].append(new_entry)
        return json.dumps(json_metadata)

    def build_user_project_entry(meta, session, row):
        update_table = sql.Table(USER_PROJECT_TABLE, meta, autoload=True)
        q = session.query(update_table)
        q = q.filter_by(user_id=row.actor_id)
        q = q.filter_by(project_id=row.target_id)
        ref = q.first()
        if ref is not None:
            values = {'data': add_to_dict_list(ref.data, row)}
            update = update_table.update().where(
                update_table.c.user_id == ref.user_id).where(
                    update_table.c.project_id == ref.project_id).values(values)
        else:
            values = {'user_id': row.actor_id,
                      'project_id': row.target_id,
                      'data': add_to_dict_list(None, row)}
            update = update_table.insert().values(values)
        return update

    def build_group_project_entry(meta, session, row):
        update_table = sql.Table(GROUP_PROJECT_TABLE, meta, autoload=True)
        q = session.query(update_table)
        q = q.filter_by(group_id=row.actor_id)
        q = q.filter_by(project_id=row.target_id)
        ref = q.first()
        if ref is not None:
            values = {'data': add_to_dict_list(ref.data, row)}
            update = update_table.update().where(
                update_table.c.group_id == ref.group_id).where(
                    update_table.c.project_id == ref.project_id).values(values)
        else:
            values = {'group_id': row.actor_id,
                      'project_id': row.target_id,
                      'data': add_to_dict_list(None, row)}
            update = update_table.insert().values(values)
        return update

    def build_user_domain_entry(meta, session, row):
        update_table = sql.Table(USER_DOMAIN_TABLE, meta, autoload=True)
        q = session.query(update_table)
        q = q.filter_by(user_id=row.actor_id)
        q = q.filter_by(domain_id=row.target_id)
        ref = q.first()
        if ref is not None:
            values = {'data': add_to_dict_list(ref.data, row)}
            update = update_table.update().where(
                update_table.c.user_id == ref.user_id).where(
                    update_table.c.domain_id == ref.domain_id).values(values)
        else:
            values = {'user_id': row.actor_id,
                      'domain_id': row.target_id,
                      'data': add_to_dict_list(None, row)}
            update = update_table.insert().values(values)
        return update

    def build_group_domain_entry(meta, session, row):
        update_table = sql.Table(GROUP_DOMAIN_TABLE, meta, autoload=True)
        q = session.query(update_table)
        q = q.filter_by(group_id=row.actor_id)
        q = q.filter_by(domain_id=row.target_id)
        ref = q.first()
        if ref is not None:
            values = {'data': add_to_dict_list(ref.data, row)}
            update = update_table.update().where(
                update_table.c.group_id == ref.group_id).where(
                    update_table.c.domain_id == ref.domain_id).values(values)
        else:
            values = {'group_id': row.actor_id,
                      'domain_id': row.target_id,
                      'data': add_to_dict_list(None, row)}
            update = update_table.insert().values(values)
        return update

    def build_update(meta, session, row):
        """Build an update or an insert to the correct metadata table."""
        if row.type == USER_PROJECT_TYPE:
            return build_user_project_entry(meta, session, row)
        elif row.type == GROUP_PROJECT_TYPE:
            return build_group_project_entry(meta, session, row)
        elif row.type == USER_DOMAIN_TYPE:
            return build_user_domain_entry(meta, session, row)
        elif row.type == GROUP_DOMAIN_TYPE:
            return build_group_domain_entry(meta, session, row)
        # If the row type doesn't match any that we understand we drop
        # the data.

    session = sql.orm.sessionmaker(bind=migrate_engine)()
    downgrade_table = sql.Table('assignment', meta, autoload=True)
    for assignment in session.query(downgrade_table).all():
        update = build_update(meta, session, assignment)
        if update is not None:
            migrate_engine.execute(update)
    session.commit()
    session.close()


def recreate_grant_tables(meta, migrate_engine):
    sql.Table('user', meta, autoload=True)
    sql.Table('group', meta, autoload=True)
    sql.Table('project', meta, autoload=True)
    sql.Table('domain', meta, autoload=True)

    user_project_metadata_table = sql.Table(
        USER_PROJECT_TABLE,
        meta,
        sql.Column(
            'user_id',
            sql.String(64),
            primary_key=True),
        sql.Column(
            'project_id',
            sql.String(64),
            sql.ForeignKey('project.id'),
            primary_key=True),
        sql.Column('data', sql.Text()))
    user_project_metadata_table.create(migrate_engine, checkfirst=True)

    group_project_metadata_table = sql.Table(
        GROUP_PROJECT_TABLE,
        meta,
        sql.Column(
            'group_id',
            sql.String(64),
            primary_key=True),
        sql.Column(
            'project_id',
            sql.String(64),
            sql.ForeignKey('project.id'),
            primary_key=True),
        sql.Column('data', sql.Text()))
    group_project_metadata_table.create(migrate_engine, checkfirst=True)

    user_domain_metadata_table = sql.Table(
        USER_DOMAIN_TABLE,
        meta,
        sql.Column(
            'user_id',
            sql.String(64),
            primary_key=True),
        sql.Column(
            'domain_id',
            sql.String(64),
            sql.ForeignKey('domain.id'),
            primary_key=True),
        sql.Column('data', sql.Text()))
    user_domain_metadata_table.create(migrate_engine, checkfirst=True)

    group_domain_metadata_table = sql.Table(
        GROUP_DOMAIN_TABLE,
        meta,
        sql.Column(
            'group_id',
            sql.String(64),
            primary_key=True),
        sql.Column(
            'domain_id',
            sql.String(64),
            sql.ForeignKey('domain.id'),
            primary_key=True),
        sql.Column('data', sql.Text()))
    group_domain_metadata_table.create(migrate_engine, checkfirst=True)


def create_assignment_table(meta, migrate_engine):
    assignment_table = sql.Table(
        'assignment',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('type', sql.Integer, nullable=False),
        sql.Column('actor_id', sql.String(64), nullable=False),
        sql.Column('target_id', sql.String(64), nullable=False),
        sql.Column('role_id', sql.String(64), nullable=False),
        sql.Column('inherited', sql.Boolean, nullable=False, default=True),
        sql.UniqueConstraint('type', 'actor_id', 'target_id', 'role_id',
                             'inherited'))
    assignment_table.create(migrate_engine, checkfirst=True)


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    create_assignment_table(meta, migrate_engine)

    session = sql.orm.sessionmaker(bind=migrate_engine)()
    for table_name in GRANT_TABLES:
        migrate_grant_table(meta, migrate_engine, session, table_name)
    session.commit()
    session.close()

    for table_name in GRANT_TABLES:
        grant_table = sql.Table(table_name, meta, autoload=True)
        grant_table.drop(migrate_engine, checkfirst=True)


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    recreate_grant_tables(meta, migrate_engine)
    downgrade_assignment_table(meta, migrate_engine)

    assignment = sql.Table('assignment', meta, autoload=True)
    assignment.drop(migrate_engine, checkfirst=True)
