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
    user_table = sql.Table('user', meta, autoload=True)
    project_table = sql.Table('project', meta, autoload=True)

    fk = migrate.ForeignKeyConstraint(columns=[user_table.c.domain_id],
                                      refcolumns=[project_table.c.id])
    if migrate_engine.name == 'mysql':
        get_fk_name = sql.text("SELECT constraint_name "
                               "FROM information_schema.key_column_usage "
                               "WHERE table_schema = 'keystone' "
                               "AND table_name = 'user' "
                               "AND column_name = 'domain_id' "
                               "AND referenced_table_name = 'project' "
                               "AND referenced_column_name = 'id'")
        result = migrate_engine.execute(get_fk_name)
        fk_name = [row for row in result][0][0]
        fk.name = fk_name
    else:
        # not sure if pg is smarter here
        pass
    fk.drop()
