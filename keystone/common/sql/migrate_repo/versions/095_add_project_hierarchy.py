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
import uuid

from keystone.common import sql as ks_sql


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
        sql.Column('depth', sql.Integer(), nullable=False, default=1),
        sql.Column('extra', ks_sql.JsonBlob.impl))
    project_hierarchy.create()

    project = sql.Table(PROJECT_TABLE, meta, autoload=True)
    migrate.ForeignKeyConstraint(columns=[project_hierarchy.c.parent_id],
                                 refcolumns=[project.c.id]).create()
    migrate.ForeignKeyConstraint(columns=[project_hierarchy.c.child_id],
                                 refcolumns=[project.c.id]).create()

    # update project_hierarchy using parent relationships
    project_select = sql.select([project], project.c.parent_id != None,  # noqa
                                use_labels=True)
    link_values = []
    for row in project_select.execute():
        link_values.append({'id': uuid.uuid4().hex,
                            'parent_id': row[project.c.parent_id],
                            'child_id': row[project.c.id], 'depth': 1})
        if len(link_values) == 100:
            project_hierarchy.insert().values(link_values).execute()
            link_values = []
    if len(link_values):
        project_hierarchy.insert().values(link_values).execute()
        link_values = []

    project_hierarchy_2 = sql.alias(project_hierarchy)
    j = project_hierarchy.join(
        project_hierarchy_2,
        project_hierarchy.c.parent_id == project_hierarchy_2.c.child_id)
    link_select = sql.select([project_hierarchy_2.c.parent_id,
                              project_hierarchy.c.child_id,
                              project_hierarchy_2.c.depth],
                             use_labels=True, from_obj=j)
    exist = True
    while exist:
        for row in link_select.execute():
            link_values.append({
                'id': uuid.uuid4().hex,
                'parent_id': row[project_hierarchy_2.c.parent_id],
                'child_id': row[project_hierarchy.c.child_id],
                'depth': row[project_hierarchy_2.c.depth] + 1
            })
            if len(link_values) == 100:
                project_hierarchy.insert().values(link_values).execute()
                link_values = []
        else:
            exist = False
        if len(link_values):
            project_hierarchy.insert().values(link_values).execute()
            link_values = []
