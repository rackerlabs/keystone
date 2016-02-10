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

import sqlalchemy as sql

from keystone.common.sql import migration_helpers


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    identity_table = sql.Table('identity', meta, autoload=False)
    if not identity_table.exists():
        user_table = sql.Table('user', meta, autoload=True)
        user_group_table = sql.Table('user_group_membership', meta,
                                     autoload=True)

        # remove user indexes and contstraints
        if migrate_engine.name != 'sqlite':
            for index in user_table.indexes:
                index.drop(migrate_engine)
            fk_constraint = [{'table': user_group_table,
                              'fk_column': 'user_id',
                              'ref_column': user_table.c.id}]
            migration_helpers.remove_constraints(fk_constraint)

        # allow domain_id and name to be null for now
        # will drop these columns in a subsequent release
        user_table.c.domain_id.alter(nullable=True)
        user_table.c.name.alter(nullable=True)

        # rename user table to identity
        user_table.rename('identity')

        # add user_group_membership fk contstraint back
        identity_table = sql.Table('identity', meta, autoload=True)
        if migrate_engine.name != 'sqlite':
            constraint = [{'table': user_group_table,
                           'fk_column': 'user_id',
                           'ref_column': identity_table.c.id}]
            migration_helpers.add_constraints(constraint)
