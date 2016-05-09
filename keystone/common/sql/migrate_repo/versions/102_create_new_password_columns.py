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


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    # add columns to the password table
    password_table = sql.Table('password', meta, autoload=True)
    created_at_column = sql.Column('created_at', sql.DateTime(), nullable=True)
    password_table.create_column(created_at_column)
    expires_at_column = sql.Column('expires_at', sql.DateTime(), nullable=True)
    password_table.create_column(expires_at_column)
    
    # add user activity table
    user_activity_table = sql.Table(
        'user_activity',
        meta,
        sql.Column('id', sql.Integer, primary_key=True, nullable=False),
        sql.Column('user_id', sql.String(64),
                   sql.ForeignKey(user_table.c.id, ondelete='CASCADE'),
                   nullable=True),
        sql.Column('user_name', sql.String(255), nullable=True),
        sql.Column('attempted_at', sql.DateTime(), nullable=False),
        sql.Column('is_success', sql.Boolean, nullable=False),
        sql.Column('message', sql.Text(), nullable=True))
    user_activity_table.create(migrate_engine, checkfirst=True)