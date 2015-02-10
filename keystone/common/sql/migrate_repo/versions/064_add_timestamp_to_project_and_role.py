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

_PROJECT_TABLE_NAME = 'project'
_ROLE_TABLE_NAME = 'role'


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    project_create_at_column = sql.Column('created_at', sql.DATETIME())
    project_udpate_at_column = sql.Column('updated_at', sql.DATETIME())
    project_table = sql.Table(_PROJECT_TABLE_NAME, meta, autoload=True)
    project_table.create_column(project_create_at_column)
    project_table.create_column(project_udpate_at_column)

    role_create_at_column = sql.Column('created_at', sql.DATETIME())
    role_udpate_at_column = sql.Column('updated_at', sql.DATETIME())
    role_table = sql.Table(_ROLE_TABLE_NAME, meta, autoload=True)
    role_table.create_column(role_create_at_column)
    role_table.create_column(role_udpate_at_column)


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    project_table = sql.Table(_PROJECT_TABLE_NAME, meta, autoload=True)
    project_table.drop_column('created_at')
    project_table.drop_column('updated_at')

    role_table = sql.Table(_ROLE_TABLE_NAME, meta, autoload=True)
    role_table.drop_column('created_at')
    role_table.drop_column('updated_at')
