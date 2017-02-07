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
from sqlalchemy.engine import reflection

from keystone.common.sql import upgrades


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    inspector = reflection.Inspector.from_engine(migrate_engine)

    user_table = sql.Table('user', meta, autoload=True)
    local_usr_table = sql.Table('local_user', meta, autoload=True)
    nlocal_usr_table = sql.Table('nonlocal_user', meta, autoload=True)
    project_table = sql.Table('project', meta, autoload=True)

    # Drop foreign key constraints first
    fk1_name = upgrades.get_fk_name(inspector, 'local_user', 'user_id')
    fkc1 = migrate.ForeignKeyConstraint(columns=[local_usr_table.c.user_id,
                                                 local_usr_table.c.domain_id],
                                        refcolumns=[user_table.c.id,
                                                    user_table.c.domain_id],
                                        name=fk1_name)
    fkc1.drop()

    fk2_name = upgrades.get_fk_name(inspector, 'nonlocal_user', 'user_id')
    fkc2 = migrate.ForeignKeyConstraint(columns=[nlocal_usr_table.c.user_id,
                                                 nlocal_usr_table.c.domain_id],
                                        refcolumns=[user_table.c.id,
                                                    user_table.c.domain_id],
                                        name=fk2_name)
    fkc2.drop()

    fk3_name = upgrades.get_fk_name(inspector, 'user', 'domain_id')
    fkc3 = migrate.ForeignKeyConstraint(columns=[user_table.c.domain_id],
                                        refcolumns=[project_table.c.id],
                                        name=fk3_name)
    fkc3.drop()

    user_table.c.domain_id.alter(nullable=False)

    # Add foreign keys back
    fkc1.create()
    fkc2.create()
    fkc3.create()

    if upgrades.USE_TRIGGERS:
        if migrate_engine.name == 'postgresql':
            drop_trigger_stmt = 'DROP TRIGGER federated_user_insert_trigger '
            drop_trigger_stmt += 'on federated_user;'
        elif migrate_engine.name == 'mysql':
            drop_trigger_stmt = 'DROP TRIGGER federated_user_insert_trigger;'
        else:
            drop_trigger_stmt = (
                'DROP TRIGGER IF EXISTS federated_user_insert_trigger;')
        migrate_engine.execute(drop_trigger_stmt)
