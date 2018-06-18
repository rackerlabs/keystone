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


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    # For Mysql and PostgreSQL, drop the FK in limit table
    # For SQLite, drop the old tables, rename the new tables.
    if migrate_engine.name != 'sqlite':
        limit_table = sql.Table('limit', meta, autoload=True)
        project_table = sql.Table('project', meta, autoload=True)
        inspector = sql.engine.reflection.Inspector.from_engine(migrate_engine)
        for fk in inspector.get_foreign_keys('limit'):
            fkey = migrate.ForeignKeyConstraint(
                [limit_table.c.project_id],
                [project_table.c.id],
                name=fk['name'])
            fkey.drop()
    else:
        registered_limit_table = sql.Table('registered_limit', meta,
                                           autoload=True)
        registered_limit_table_new = sql.Table('registered_limit_new', meta,
                                               autoload=True)
        limit_table = sql.Table('limit', meta, autoload=True)
        limit_table_new = sql.Table('limit_new', meta, autoload=True)

        limit_table.drop()
        limit_table_new.rename('limit')
        registered_limit_table.drop()
        registered_limit_table_new.rename('registered_limit')
