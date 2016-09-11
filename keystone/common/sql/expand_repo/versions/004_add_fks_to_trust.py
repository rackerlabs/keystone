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


TRUST_TABLE = 'trust'
USER_TABLE = 'user'
PROJECT_TABLE = 'project'


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    meta = sql.MetaData()
    meta.bind = migrate_engine

    trust = sql.Table(TRUST_TABLE, meta, autoload=True)
    user = sql.Table(USER_TABLE, meta, autoload=True)
    project = sql.Table(PROJECT_TABLE, meta, autoload=True)

    fkeys = [
        {'columns': [trust.c.trustor_user_id],
         'references': [user.c.id]},
        {'columns': [trust.c.trustee_user_id],
         'references': [user.c.id]},
        {'columns': [trust.c.project_id],
         'references': [project.c.id]},
    ]

    for fkey in fkeys:
        migrate.ForeignKeyConstraint(columns=fkey['columns'],
                                     refcolumns=fkey['references'],
                                     name=fkey.get('name'),
                                     ondelete="CASCADE").create()
