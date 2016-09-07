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

import datetime

import sqlalchemy as sql
import sqlalchemy.sql.expression as expression


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    # Drop and add created_at column.
    password = sql.Table('password', meta, autoload=True)
    password.c.created_at.drop()
    created_at = sql.Column('created_at', sql.DateTime(), nullable=True,
                            default=datetime.datetime.utcnow)
    password.create_column(created_at)

    # Update the created_at value for existing passwords. Setting the date to a
    # day before to ensure that the created_at date for new password changes
    # are greater than the old password created_at during a rolling upgrade.
    create_date = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    values = {'created_at': create_date}
    stmt = password.update().where(
        password.c.created_at == expression.null()).values(values)
    stmt.execute()

    # Set created_at to be not nullable.
    password.c.created_at.alter(nullable=False)
