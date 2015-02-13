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
from sqlalchemy.orm import Session

from keystone.common import sql as ks_sql

_PROJECT_TABLE_NAME = 'project'
_DOMAIN_TABLE_NAME = 'domain'
_ORIG_PROJECT_TABLE_NAME = 'orig_project'
_IS_DOMAIN_COLUMN_NAME = 'is_domain'


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    project_table = sql.Table(_PROJECT_TABLE_NAME, meta, autoload=True)
    is_domain = sql.Column(_IS_DOMAIN_COLUMN_NAME, sql.Boolean, nullable=False,
                           server_default='0', default=False)
    project_table.create_column(is_domain)


def _downgrade_project_table_with_copy(meta, migrate_engine):
    # Used with databases that don't support dropping a column (e.g., sqlite).
    orig_project_table = sql.Table(_PROJECT_TABLE_NAME, meta, autoload=True)
    orig_project_table.deregister()
    orig_project_table.rename(_ORIG_PROJECT_TABLE_NAME)

    session = Session(bind=migrate_engine)
    with session.transaction:
        # Need to load the metadata for the domain table since it's used as
        # foreign key.
        sql.Table(
            _DOMAIN_TABLE_NAME, meta, autoload=True,
            autoload_with=session.connection())

        project_table = sql.Table(
            _PROJECT_TABLE_NAME, meta,
            sql.Column('id', sql.String(length=64), primary_key=True),
            sql.Column('name', sql.String(length=64), nullable=False),
            sql.Column('extra', ks_sql.JsonBlob.impl),
            sql.Column('description', sql.Text),
            sql.Column('enabled', sql.Boolean),
            sql.Column(
                'domain_id', sql.String(length=64),
                sql.ForeignKey('domain.id'),
                nullable=False),
            sql.Column(
                'parent_id', sql.String(length=64),
                sql.ForeignKey('project.id'),
                nullable=True))
        project_table.create(migrate_engine, checkfirst=True)

        orig_project_table = sql.Table(
            _ORIG_PROJECT_TABLE_NAME, meta, autoload=True,
            autoload_with=session.connection())
        for project in session.query(orig_project_table):
            new_values = {
                'id': project.id,
                'name': project.name,
                'extra': project.extra,
                'description': project.description,
                'enabled': project.enabled,
                'domain_id': project.domain_id,
                'parent_id': project.parent_id
            }
            session.execute('insert into ' + _PROJECT_TABLE_NAME + '(id, '
                            'name, extra, description, enabled, domain_id, '
                            'parent_id) values ( :id, :name, :extra, '
                            ':description, :enabled, :domain_id, :parent_id);',
                            new_values)
    orig_project_table.drop()


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    project_table = sql.Table(_PROJECT_TABLE_NAME, meta, autoload=True)
    if migrate_engine.name == 'sqlite':
        meta.clear()
        _downgrade_project_table_with_copy(meta, migrate_engine)
        return

    project_table.drop_column(_IS_DOMAIN_COLUMN_NAME)
