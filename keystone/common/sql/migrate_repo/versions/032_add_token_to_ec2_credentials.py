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


def downgrade_ec2_table_with_column_drop(meta, migrate_engine):
    ec2_table = sqlalchemy.Table('ec2_credential', meta, autoload=True)
    ec2_table.drop_column(
        sqlalchemy.Column('token_id',
                          sqlalchemy.String(64),
                          nullable=True))
    ec2_table.drop_column(
        sqlalchemy.Column('trustee_id',
                          sqlalchemy.String(64),
                          nullable=True))


def create_column_forgiving(migrate_engine, table, column):
    try:
        table.create_column(column)
    except exc.OperationalError as e:
        if (e.args[0].endswith('duplicate column name: %s' % column.name)
                and migrate_engine.name == "sqlite"):
                    #sqlite does not drop columns, so  if we have already
                    #done a downgrade and are now upgrading,  we will hit
                    #this: the SQLite driver previously reported success
                    #dropping the columns but it hasn't.
                    pass
        else:
            raise


def upgrade_ec2_table(meta, migrate_engine):
    ec2_table = sqlalchemy.Table('ec2_credential', meta, autoload=True)

    create_column_forgiving(
        migrate_engine, ec2_table,
        sqlalchemy.Column('trustee_id',
                          sqlalchemy.String(64),
                          nullable=True))
    create_column_forgiving(
        migrate_engine, ec2_table,
        sqlalchemy.Column('token_id',
                          sqlalchemy.String(64),
                          nullable=True))


def upgrade(migrate_engine):
    meta = sqlalchemy.MetaData()
    meta.bind = migrate_engine
    upgrade_ec2_table(meta, migrate_engine)


def downgrade(migrate_engine):
    meta = sqlalchemy.MetaData()
    meta.bind = migrate_engine
    downgrade_ec2_table_with_column_drop(meta, migrate_engine)
