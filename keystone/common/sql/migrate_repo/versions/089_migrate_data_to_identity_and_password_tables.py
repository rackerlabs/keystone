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

from migrate import ForeignKeyConstraint


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    user_table = sql.Table('user', meta, autoload=True)
    user_group_table = sql.Table('user_group_membership', meta, autoload=True)
    identity_table = sql.Table('identity', meta, autoload=True)
    password_table = sql.Table('password', meta, autoload=True)

    # TODO(rderose): may want to batch these...

    # insert identities
    identity_table.delete().execute()
    sel = sql.select([user_table.c.id, user_table.c.extra,
                      user_table.c.enabled, user_table.c.default_project_id])
    ins = identity_table.insert().from_select(['id',
                                               'extra',
                                               'enabled',
                                               'default_project_id'], sel)
    ins.execute()

    # insert passwords
    password_table.delete().execute()
    sel = sql.select([user_table.c.id, user_table.c.name,
                      user_table.c.domain_id, user_table.c.password])
    ins = password_table.insert().from_select(['identity_id',
                                               'name',
                                               'domain_id',
                                               'password'], sel)
    ins.execute()

    # update user_group_membership fk contstraint
    try:
        ForeignKeyConstraint(columns=[user_group_table.c.user_id],
                             refcolumns=[user_table.c.id]).drop()
    except Exception:
        pass

    ForeignKeyConstraint(columns=[user_group_table.c.user_id],
                         refcolumns=[identity_table.c.id]).create()


def downgrade(migrate_engine):
    pass
