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
import sqlalchemy

from keystone.common import sql


ASSIGNMENT_TABLE = 'assignment'
INHERITED_COLUMN = 'inherited'


def upgrade(migrate_engine):
    ''''Inserts inherited column to assignment table PK contraints.'''

    # SQLite does not support constraints, and querying the constraints
    # raises an exception
    if migrate_engine.name == 'sqlite':
        return

    meta = sqlalchemy.MetaData()
    meta.bind = migrate_engine
    assignment_table = sqlalchemy.Table(ASSIGNMENT_TABLE, meta, autoload=True)

    migrate.PrimaryKeyConstraint(table=assignment_table).drop()
    getattr(assignment_table.c, INHERITED_COLUMN).alter(primary_key=True)
    migrate.PrimaryKeyConstraint(table=assignment_table).create()

def downgrade(migrate_engine):
    ''''Removes inherited column from assignment table PK contraints.'''

    if migrate_engine.name == 'sqlite':
        return

    meta = sqlalchemy.MetaData()
    meta.bind = migrate_engine
    assignment_table = sqlalchemy.Table(ASSIGNMENT_TABLE, meta, autoload=True)

    migrate.PrimaryKeyConstraint(table=assignment_table).drop()
    getattr(assignment_table.c, INHERITED_COLUMN).alter(primary_key=False)
    migrate.PrimaryKeyConstraint(table=assignment_table).create()
