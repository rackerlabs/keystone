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


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    # hardcoding in the server_default as mysql 5.5 doesn't support func.now()
    created_at = sql.Column('created_at', sql.DateTime(), nullable=False,
                            default=datetime.datetime.utcnow,
                            server_default='2016-08-29 00:00:00')
    expires_at = sql.Column('expires_at', sql.DateTime(), nullable=True)
    password_table = sql.Table('password', meta, autoload=True)
    password_table.create_column(created_at)
    password_table.create_column(expires_at)
    # overwriting the created_at hardcoded value
    now = datetime.datetime.utcnow()
    stmt = password_table.update().values(created_at=now)
    stmt.execute()
