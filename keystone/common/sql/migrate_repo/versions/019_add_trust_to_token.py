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


import sqlalchemy
from sqlalchemy import exc
from sqlalchemy.orm import sessionmaker
from keystone import config


def downgrade_token_table_with_column_drop(meta, migrate_engine):
    token_table = sqlalchemy.Table('token', meta, autoload=True)
    token_table.drop_column(
        sqlalchemy.Column('trust_id',
                          sqlalchemy.String(128),
                          nullable=True))
    token_table.drop_column(
        sqlalchemy.Column('user_id',
                          sqlalchemy.String(128)))


def upgrade_token_table(meta, migrate_engine):
    token_table = sqlalchemy.Table('token', meta, autoload=True)
    try:
        token_table.create_column(
            sqlalchemy.Column('trust_id',
                              sqlalchemy.String(128),
                              nullable=True))
    #sqlite does not drop columns, so if we hit this,
    #it thinks it has dropped them, but it hasn't
    except exc.OperationalError as e:
        if e.args[0].endswith('duplicate column name: trust_id'):
            pass
        else:
            raise(e)
    try:
        token_table.create_column(
            sqlalchemy.Column('user_id', sqlalchemy.String(128)))
    except exc.OperationalError as e:
        if e.args[0].endswith('duplicate column name: user_id'):
            pass
        else:
            raise(e)


def upgrade(migrate_engine):
    meta = sqlalchemy.MetaData()
    meta.bind = migrate_engine
    upgrade_token_table(meta, migrate_engine)


def downgrade(migrate_engine):
    meta = sqlalchemy.MetaData()
    meta.bind = migrate_engine
    downgrade_token_table_with_column_drop(meta, migrate_engine)
