# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
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
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    meta = sql.MetaData()
    meta.bind = migrate_engine

    consumer_table = sql.Table(
        'consumer',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(64)),
        sql.Column('consumer_key', sql.String(64)),
        sql.Column('consumer_secret', sql.String(64)),
        sql.Column('domain_id', sql.String(64)),
        sql.Column('extra', sql.Text()))
    consumer_table.create(migrate_engine, checkfirst=True)

    request_token_table = sql.Table(
        'request_token',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('key', sql.String(64)),
        sql.Column('key_hash', sql.String(255)),
        sql.Column('secret', sql.String(64)),
        sql.Column('verifier', sql.String(64)),
        sql.Column('user_id', sql.String(64)),
        sql.Column('tenant_id', sql.String(64)),
        sql.Column('requested_roles', sql.Text()),
        sql.Column('consumer_key', sql.String(64)),
        sql.Column('issued_at', sql.String(64)))
    request_token_table.create(migrate_engine, checkfirst=True)

    access_token_table = sql.Table(
        'access_token',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('key', sql.String(64)),
        sql.Column('secret', sql.String(64)),
        sql.Column('user_id', sql.String(64)),
        sql.Column('tenant_id', sql.String(64)),
        sql.Column('requested_roles', sql.Text()),
        sql.Column('consumer_key', sql.String(64)),
        sql.Column('issued_at', sql.String(64)))
    access_token_table.create(migrate_engine, checkfirst=True)


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    # Operations to reverse the above upgrade go here.
    for table_name in ['consumer']:
        table = sql.Table(table_name, meta, autoload=True)
        table.drop()
