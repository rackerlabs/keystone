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

_ROLE_TABLE_NAME = 'role'
_ROLE_NAME_COLUMN_NAME = 'name'


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    role_table = sql.Table(_ROLE_TABLE_NAME, meta, autoload=True)

    # NOTE(morganfainberg): the `role_name` unique constraint is not
    # guaranteed to be named 'ixu_role_name', so we need to search for the
    # correct constraint that only affects role_table.c.name and drop
    # that constraint.
    #
    # This is an idempotent change that reflects the fix to migration
    # 88 if the role_name unique constraint was not named consistently.
    # This is a copy of migration 96 to catch any/all deployments that
    # are close to master. migration 96 will be backported to
    # stable/mitaka.
    constraints_to_drop = []
    for c in role_table.constraints:
        if isinstance(c, sql.UniqueConstraint):
            if len(c.columns) == 1 and _ROLE_NAME_COLUMN_NAME in c.columns:
                constraints_to_drop.append(c)

    for c in constraints_to_drop:
        migrate.UniqueConstraint(role_table.c.name, name=c.name).drop()
