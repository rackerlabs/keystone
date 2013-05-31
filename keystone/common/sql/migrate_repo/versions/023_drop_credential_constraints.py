# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack LLC
#
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

from migrate import ForeignKeyConstraint
import sqlalchemy


def get_constraint_name(table, column_name):
    fkeys = [fk for fk in table.constraints if column_name in fk.columns]
    constraint_name = fkeys[0].name
    return constraint_name


def remove_constraints(migrate_engine):
    if migrate_engine.name == 'sqlite':
        return
    meta = sqlalchemy.MetaData()
    meta.bind = migrate_engine
    user_table = sqlalchemy.Table('user', meta, autoload=True)
    proj_table = sqlalchemy.Table('project', meta, autoload=True)
    cred_table = sqlalchemy.Table('credential', meta, autoload=True)
    ForeignKeyConstraint(columns=[cred_table.c.user_id],
                         refcolumns=[user_table.c.id],
                         name=get_constraint_name(cred_table, 'user_id')
                         ).drop()
    ForeignKeyConstraint(columns=[cred_table.c.project_id],
                         refcolumns=[proj_table.c.id],
                         name=get_constraint_name(cred_table, 'project_id')
                         ).drop()


def add_constraints(migrate_engine):
    if migrate_engine.name == 'sqlite':
        return
    meta = sqlalchemy.MetaData()
    meta.bind = migrate_engine
    user_table = sqlalchemy.Table('user', meta, autoload=True)
    proj_table = sqlalchemy.Table('project', meta, autoload=True)
    cred_table = sqlalchemy.Table('credential', meta, autoload=True)
    ForeignKeyConstraint(columns=[cred_table.c.user_id],
                         refcolumns=[user_table.c.id]).create()
    ForeignKeyConstraint(columns=[cred_table.c.project_id],
                         refcolumns=[proj_table.c.id]).create()


def upgrade(migrate_engine):
    remove_constraints(migrate_engine)


def downgrade(migrate_engine):
    add_constraints(migrate_engine)
