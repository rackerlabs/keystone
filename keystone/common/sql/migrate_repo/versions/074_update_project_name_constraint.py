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

import migrate
import sqlalchemy as sql

from keystone.common.sql import migration_helpers

_PROJECT_NAME_OLD_CONSTRAINT = 'ixu_project_name_domain_id'
_PROJECT_NAME_NEW_CONSTRAINT = 'ixu_project_name_domain_id_is_domain'
_PROJECT_TABLE_NAME = 'project'
_DOMAIN_TABLE_NAME = 'domain'
_DOMAIN_ID_COLUMN_NAME = 'domain_id'


def list_constraints(domain_table, project_table):
    constraints = [{'table': project_table,
                    'fk_column': _DOMAIN_ID_COLUMN_NAME,
                    'ref_column': domain_table.c.id}]

    return constraints


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    domain_table = sql.Table(_DOMAIN_TABLE_NAME, meta, autoload=True)
    project_table = sql.Table(_PROJECT_TABLE_NAME, meta, autoload=True)

    if migrate_engine.name != 'sqlite':
        migration_helpers.remove_constraints(list_constraints(domain_table,
                                                              project_table))

    migrate.UniqueConstraint(project_table.c.domain_id,
                             project_table.c.name,
                             name=_PROJECT_NAME_OLD_CONSTRAINT).drop()

    if migrate_engine.name != 'sqlite':
        migration_helpers.add_constraints(list_constraints(domain_table,
                                                           project_table))

    migrate.UniqueConstraint(project_table.c.domain_id,
                             project_table.c.name,
                             project_table.c.is_domain,
                             name=_PROJECT_NAME_NEW_CONSTRAINT).create()
