# Copyright 2016 Intel Corporation
# All Rights Reserved
#
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

# TODO(xek): move to migrate_repo in Newton cycle

import migrate
from sqlalchemy import MetaData, Table, and_, or_

from keystone.common import sql

_ASSIGNMENT_TABLE_NAME = 'assignment'
_ASSIGNMENT_COLUMN_NAMES = ('actor_id_bin', 'target_id_bin', 'role_id_bin')
_ASSIGNMENT_OLD_COLUMN_NAMES = ('actor_id', 'target_id', 'role_id')


def upgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)
    assignment_table = Table(_ASSIGNMENT_TABLE_NAME, meta, autoload=True)

    def get_columns(column_names):
        return [getattr(assignment_table.c, column_name)
                for column_name in column_names]

    # ensure all data is migrated
    assignments = list(assignment_table.select(
        or_(*[column.is_(None) for column
              in get_columns(_ASSIGNMENT_COLUMN_NAMES)]),
        for_update='read'
    ).execute())
    for assignment in assignments:
        new_values = {new_name:
                      sql.BinaryHex().process_bind_param(
                          getattr(assignment, old_name), migrate_engine)
                      for new_name, old_name
                      in zip(_ASSIGNMENT_COLUMN_NAMES,
                             _ASSIGNMENT_OLD_COLUMN_NAMES)}
        update = assignment_table.update().where(and_(
            assignment_table.c.type == assignment.type,
            assignment_table.c.actor_id == assignment.actor_id,
            assignment_table.c.target_id == assignment.target_id,
            assignment_table.c.role_id == assignment.role_id,
            assignment_table.c.inherited == assignment.inherited)
        ).values(new_values)
        migrate_engine.execute(update)

    # alter columns
    for column_name in _ASSIGNMENT_COLUMN_NAMES:
        getattr(assignment_table.c, column_name).alter(nullable=False)

    def _primary_key(diff_columns):
        return ('type',) + diff_columns + ('inherited',)
    # delete old primary key constraint
    migrate.PrimaryKeyConstraint(*_primary_key(_ASSIGNMENT_OLD_COLUMN_NAMES),
                                 table=assignment_table).drop()
    # create new primary key constraint
    migrate.PrimaryKeyConstraint(*_primary_key(_ASSIGNMENT_COLUMN_NAMES),
                                 table=assignment_table).create()
    # delete old columns
    for column_name in _ASSIGNMENT_OLD_COLUMN_NAMES:
        getattr(assignment_table.c, column_name).drop()
    # create index for actor_id
    idx = sql.Index('ix_actor_id', assignment.c.actor_id_bin)
    idx.create(migrate_engine)
