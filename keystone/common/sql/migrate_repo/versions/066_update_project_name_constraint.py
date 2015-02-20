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

_PROJECT_TABLE_NAME = 'project'
_PROJECT_NAME_DOMAIN_ID_CONSTRAINT = 'ixu_project_name_domain_id'


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    project_table = sql.Table(_PROJECT_TABLE_NAME, meta, autoload=True)

    migrate.UniqueConstraint(project_table.c.domain_id,
                             project_table.c.name,
                             name=_PROJECT_NAME_DOMAIN_ID_CONSTRAINT).drop()


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    project_table = sql.Table(_PROJECT_TABLE_NAME, meta, autoload=True)

    migrate.UniqueConstraint(project_table.c.domain_id,
                             project_table.c.name,
                             name=_PROJECT_NAME_DOMAIN_ID_CONSTRAINT).create()
