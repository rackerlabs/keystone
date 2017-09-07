#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import sqlalchemy as sql

from keystone.common.sql import upgrades


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    # Approach 4b from
    # https://etherpad.openstack.org/p/keystone-non-enum-migration
    assignment_table_name = 'assignment'
    assignment_table = sql.Table(assignment_table_name, meta, autoload=True)

    # Drop the `assignment.type` column
    assignment_table.c.type.drop()

    # Remove the read-only triggers
    if upgrades.USE_TRIGGERS:
        if migrate_engine.name == 'postgresql':
            drop_assignment_update_trigger = (
                'DROP TRIGGER assignment_update_read_only on credential;'
            )
            drop_assignment_insert_trigger = (
                'DROP TRIGGER assignment_insert_read_only on credential;'
            )
        elif migrate_engine.name == 'mysql':
            drop_assignment_update_trigger = (
                'DROP TRIGGER assignment_update_read_only;'
            )
            drop_assignment_insert_trigger = (
                'DROP TRIGGER assignment_insert_read_only;'
            )
        else:
            # NOTE(lbragstad): Apparently sqlalchemy and sqlite behave weird
            # when using triggers, which is why we use the `IF EXISTS`
            # conditional here. I think what is happening is that the
            # assignment_table.c.type.drop() causes sqlalchemy to create a new
            # assignment table - but it doesn't copy the triggers over, which
            # causes the DROP TRIGGER statement to fail without `IF EXISTS`
            # because the trigger doesn't exist in the new table(?!).
            drop_assignment_update_trigger = (
                'DROP TRIGGER IF EXISTS assignment_update_read_only;'
            )
            drop_assignment_insert_trigger = (
                'DROP TRIGGER IF EXISTS assignment_insert_read_only;'
            )
        migrate_engine.execute(drop_assignment_update_trigger)
        migrate_engine.execute(drop_assignment_insert_trigger)

    # Make the `assignment_type` column non-nullable and fixup any indexes if
    # necessary
    assignment_table.c.assignment_type.alter(nullable=False)
