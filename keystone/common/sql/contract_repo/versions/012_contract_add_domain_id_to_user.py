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

from keystone.common.sql import upgrades


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    user = sql.Table('user', meta, autoload=True)
    local_user = sql.Table('local_user', meta, autoload=True)
    nonlocal_user = sql.Table('nonlocal_user', meta, autoload=True)

    # drop previous fk constraints
    migrate.ForeignKeyConstraint(
        columns=[local_user.c.user_id],
        refcolumns=[user.c.id]).drop()

    migrate.ForeignKeyConstraint(
        columns=[nonlocal_user.c.user_id],
        refcolumns=[user.c.id]).drop()

    # create new fk and unique constraints
    migrate.UniqueConstraint(user.c.id, user.c.domain_id,
                             name='ixu_user_id_domain_id').create()
    migrate.ForeignKeyConstraint(
        columns=[local_user.c.user_id, local_user.c.domain_id],
        refcolumns=[user.c.id, user.c.domain_id],
        onupdate='CASCADE', ondelete='CASCADE').create()
    migrate.ForeignKeyConstraint(
        columns=[nonlocal_user.c.user_id, nonlocal_user.c.domain_id],
        refcolumns=[user.c.id, user.c.domain_id],
        onupdate='CASCADE', ondelete='CASCADE').create()

    # drop triggers
    if upgrades.USE_TRIGGERS:
        if migrate_engine.name == 'postgresql':
            drop_user_insert_trigger = (
                'DROP TRIGGER user_insert_read_only on user;'
            )
        elif migrate_engine.name == 'mysql':
            drop_user_insert_trigger = (
                'DROP TRIGGER user_insert_read_only;'
            )
        else:
            drop_user_insert_trigger = (
                'DROP TRIGGER IF EXISTS user_insert_read_only;'
            )
        migrate_engine.execute(drop_user_insert_trigger)
