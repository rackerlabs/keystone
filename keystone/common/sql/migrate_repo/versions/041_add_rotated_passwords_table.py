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

    sql.Table('user', meta, autoload=True)

    rotated_password = sql.Table(
        'rotated_password',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('user_id',
                   sql.String(64),
                   sql.ForeignKey('user.id'),
                   nullable=False,
                   index=True),
        sql.Column('password', sql.String(128), nullable=False),
        sql.Column("created_at",
                   sql.types.DateTime,
                   nullable=False,
                   default=datetime.datetime.utcnow),
        sql.Column("expires_at",
                   sql.types.DateTime,
                   nullable=True,
                   index=True))
    rotated_password.create(migrate_engine, checkfirst=True)


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    table = sql.Table('rotated_password', meta, autoload=True)
    table.drop(migrate_engine, checkfirst=True)
