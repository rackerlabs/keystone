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


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    # Approach 3b from
    # https://etherpad.openstack.org/p/keystone-non-enum-migration
    assignment_table_name = 'assignment'
    assignment_table = sql.Table(assignment_table_name, meta, autoload=True)
    session = sql.orm.sessionmaker(bind=migrate_engine)()

    # Migrate all `assignment.type` to `assignment.assignment_type`
    assignments = list(assignment_table.select().execute())
    for assignment in assignments:
        assignment_type = assignment.type
        values = {'assignment_type': assignment_type}
        update = assignment_table.update().where(
            assignment_table.c.type == assignment.type).where(
            assignment_table.c.actor_id == assignment.actor_id).where(
            assignment_table.c.target_id == assignment.target_id).where(
            assignment_table.c.role_id == assignment.role_id).where(
            assignment_table.c.inherited == assignment.inherited).values(
                values)
        session.execute(update)
        session.commit()
    session.close()
