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
import sqlalchemy as sql

from keystone.common.sql import migration_helpers

_PROJECT_TABLE_NAME = 'project'
_DOMAIN_TABLE_NAME = 'domain'
_PARENT_ID_COLUMN_NAME = 'parent_id'


def list_parent_constraints(project_table):
    constraints = [{'table': project_table,
                    'fk_column': _PARENT_ID_COLUMN_NAME,
                    'ref_column': project_table.c.id}]

    return constraints


def upgrade(migrate_engine):

    def _get_project_from_domain(domain):
        """Creates an is_domain project ref from the provided domain."""

        # 'description' property is an extra attritbute in domains
        description = None
        extra = domain.extra
        if extra is not None:
            description = json.loads(extra).get('description', 'None')

        project_ref = {
            'id': domain.id,
            'name': domain.name,
            'enabled': domain.enabled,
            'description': description,
            'domain_id': domain.id,
            'is_domain': True,
            'parent_id': None,
            'extra': '{}'
        }

        return project_ref

    meta = sql.MetaData()
    meta.bind = migrate_engine
    session = sql.orm.sessionmaker(bind=migrate_engine)()

    project_table = sql.Table(_PROJECT_TABLE_NAME, meta, autoload=True)
    domain_table = sql.Table(_DOMAIN_TABLE_NAME, meta, autoload=True)

    # NOTE(htruta): Remove the parent_id constraint during the migration
    # because for every root project inside this domain, we will set
    # the domain_id to be the parent_id. We re-enable the constraint
    # in the end of this method.
    if migrate_engine.name != 'sqlite':
        migration_helpers.remove_constraints(
            list_parent_constraints(project_table))

    domains = list(domain_table.select().execute())
    for domain in domains:
        # Create an is_domain project based on the created domain
        is_domain_project = _get_project_from_domain(domain)
        new_entry = project_table.insert().values(**is_domain_project)
        session.execute(new_entry)
        session.commit()

    projects = list(project_table.select().execute())
    for project in projects:
        if (project.parent_id is None and not project.is_domain):
            # Update the project parent_id to be its domain_id
            values = {'parent_id': project.domain_id}
            update = project_table.update().where(
                project_table.c.id == project.id).values(values)
            session.execute(update)
            session.commit()

    if migrate_engine.name != 'sqlite':
        migration_helpers.add_constraints(
            list_parent_constraints(project_table))

    session.close()
