# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack Foundation
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

    # catalog

    service_table = sql.Table(
        'revoked_token',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('scope_id', sql.String(64)),
        sql.Column('scope_type', sql.Integer()),
        sql.Column('issued_at_or_after', sql.DateTime()),
        sql.Column('issued_at_or_before', sql.DateTime()),
        sql.Column('expires_at_or_after', sql.DateTime()),
        sql.Column('expires_at_or_before', sql.DateTime())),
    service_table.create(migrate_engine, checkfirst=True)


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    meta = sql.MetaData()
    meta.bind = migrate_engine

    tables = ['revoked_token']
    for t in tables:
        table = sql.Table(t, meta, autoload=True)
        table.drop(migrate_engine, checkfirst=True)
