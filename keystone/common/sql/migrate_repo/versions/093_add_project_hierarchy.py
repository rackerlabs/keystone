#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import migrate
import sqlalchemy as sql


PROJECT_HIERARCHY_TABLE = 'project_hierarchy'
PROJECT_TABLE = 'project'


def upgrade(migrate_engine):

    meta = sql.MetaData()
    meta.bind = migrate_engine

    project_hierarchy = sql.Table(
        PROJECT_HIERARCHY_TABLE,
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('parent_id', sql.String(length=64), nullable=False),
        sql.Column('child_id', sql.String(length=64), nullable=False),
        sql.Column('depth', sql.Integer(), nullable=False), default=1)
    project_hierarchy.create()

    project = sql.Table(PROJECT_TABLE, meta, autoload=True)
    migrate.ForeignKeyConstraint(columns=[project_hierarchy.c.parent_id],
                                 references=[project.c.id]).create()
    migrate.ForeignKeyConstraint(columns=[project_hierarchy.c.child_id],
                                 references=[project.c.id]).create()

    # TODO(amakarov): update project_hierarchy using parent relationships