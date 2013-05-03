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

import sqlalchemy as sql


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    table = sql.Table(
        'token_archive',
        meta,
        sql.Column('id', sql.String(64)),
        sql.Column('expires', sql.DateTime()),
        sql.Column('extra', sql.Text()),
        sql.Column('valid', sql.Boolean(), nullable=False),
        sql.Column('trust_id', sql.String(64), nullable=True),
        sql.Column('user_id', sql.String(64), nullable=True))
    table.create(migrate_engine, checkfirst=True)


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    migrate_engine.execute('INSERT INTO token SELECT * FROM token_archive')

    archive_table = sql.Table('token_archive', meta, autoload=True)
    archive_table.drop(migrate_engine, checkfirst=True)
