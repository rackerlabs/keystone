# Copyright 2014 IBM Corp.
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

import sqlalchemy as sql
from sqlalchemy.orm import sessionmaker

from keystone.identity.backends import sql as identity_sql
from keystone.identity import core


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    upgrade_table = sql.Table('user', meta, autoload=True)
    upgrade_table.c.id.alter(type=identity_sql.ENTITY_ID_TYPE)
    upgrade_table = sql.Table('group', meta, autoload=True)
    upgrade_table.c.id.alter(type=identity_sql.ENTITY_ID_TYPE)
    upgrade_table = sql.Table('user_group_membership', meta, autoload=True)
    upgrade_table.c.user_id.alter(type=identity_sql.ENTITY_ID_TYPE)
    upgrade_table.c.group_id.alter(type=identity_sql.ENTITY_ID_TYPE)
    upgrade_table = sql.Table('assignment', meta, autoload=True)
    upgrade_table.c.actor_id.alter(type=identity_sql.ENTITY_ID_TYPE)


def downgrade(migrate_engine):

    def truncate():
        if migrate_engine.name != 'mysql':
            # NOTE(aloga): sqlite does not enforce length on the
            # VARCHAR types: http://www.sqlite.org/faq.html#q9
            # postgresql and DB2 do not truncate.
            maker = sessionmaker(bind=migrate_engine)
            session = maker()

            # Since all the items we are changing are either prime or
            # foreign keys, we have to drop any rows for which the
            # attribute is now too big.
            for row in session.query(user_table).all():
                if core.COMPOSITE_ID_SEPERATOR in row.id:
                    update = user_table.delete().where(
                        user_table.c.id == row.id)
                    migrate_engine.execute(update)

            for row in session.query(group_table).all():
                if core.COMPOSITE_ID_SEPERATOR in row.id:
                    update = group_table.delete().where(
                        group_table.c.id == row.id)
                    migrate_engine.execute(update)

            for row in session.query(membership_table).all():
                if (core.COMPOSITE_ID_SEPERATOR in row.user_id or
                        core.COMPOSITE_ID_SEPERATOR in row.group_id):
                    update = membership_table.delete().where(
                        membership_table.c.user_id == row.user_id).where(
                            membership_table.c.group_id == row.group_id)
                    migrate_engine.execute(update)

            for row in session.query(assignment_table).all():
                if core.COMPOSITE_ID_SEPERATOR in row.actor_id:
                    update = assignment_table.delete().where(
                        assignment_table.c.actor_id == row.actor_id)
                    migrate_engine.execute(update)

            session.commit()
            session.close()

    meta = sql.MetaData()
    meta.bind = migrate_engine
    user_table = sql.Table('user', meta, autoload=True)
    group_table = sql.Table('group', meta, autoload=True)
    membership_table = sql.Table('user_group_membership', meta, autoload=True)
    assignment_table = sql.Table('assignment', meta, autoload=True)

    truncate()

    user_table.c.id.alter(type=sql.String(64))
    group_table.c.id.alter(type=sql.String(64))
    membership_table.c.user_id.alter(type=sql.String(64))
    membership_table.c.group_id.alter(type=sql.String(64))
    assignment_table.c.actor_id.alter(type=sql.String(64))
