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

    idp_table = sql.Table('identity_provider', meta, autoload=True)
    project_table = sql.Table('project', meta, autoload=True)

    # Drop foreign key constraint first
    fk_name = upgrades.get_fk_name(inspector, 'identity_provider', 'domain_id')
    fkc = migrate.ForeignKeyConstraint(columns=[idp_table.c.domain_id],
                                       refcolumns=[project_table.c.id],
                                       name=fk_name)
    fkc.drop()

    idp_table.c.domain_id.alter(nullable=False, unique=True)

    # Add foreign key back
    fkc.create()

    if upgrades.USE_TRIGGERS:
        if migrate_engine.name == 'postgresql':
            drop_idp_insert_trigger = (
                'DROP TRIGGER idp_insert_read_only on identity_provider;'
            )
        elif migrate_engine.name == 'mysql':
            drop_idp_insert_trigger = (
                'DROP TRIGGER idp_insert_read_only;'
            )
        else:
            drop_idp_insert_trigger = (
                'DROP TRIGGER IF EXISTS idp_insert_read_only;'
            )
        migrate_engine.execute(drop_idp_insert_trigger)
