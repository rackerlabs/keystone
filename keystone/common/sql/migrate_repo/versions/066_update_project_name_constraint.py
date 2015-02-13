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

_PROJECT_NAME_OLD_CONSTRAINT = 'ixu_project_name_domain_id'
_PROJECT_NAME_NEW_CONSTRAINT = 'ixu_project_name_domain_id_is_domain'
_PROJECT_TABLE_NAME = 'project'


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    project_table = sql.Table(_PROJECT_TABLE_NAME, meta, autoload=True)
    migrate.UniqueConstraint(project_table.c.domain_id,
                             project_table.c.name,
                             name=_PROJECT_NAME_OLD_CONSTRAINT).drop()
    migrate.UniqueConstraint(project_table.c.domain_id,
                             project_table.c.name,
                             project_table.c.is_domain,
                             name=_PROJECT_NAME_NEW_CONSTRAINT).create()


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    project_table = sql.Table(_PROJECT_TABLE_NAME, meta, autoload=True)
    migrate.UniqueConstraint(project_table.c.domain_id,
                             project_table.c.name,
                             project_table.c.is_domain,
                             name=_PROJECT_NAME_NEW_CONSTRAINT).drop()
    migrate.UniqueConstraint(project_table.c.domain_id,
                             project_table.c.name,
                             name=_PROJECT_NAME_OLD_CONSTRAINT).create()
