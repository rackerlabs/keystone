#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import sqlalchemy as sql

from keystone.common import sql as ks_sql


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    user_table = sql.Table('user', meta, autoload=True)

    user_mfa_rules_table = sql.Table(
        'user_mfa_auth_rules',
        meta,
        sql.Column('id', sql.Integer, primary_key=True, nullable=False),
        sql.Column('user_id', sql.String(64), sql.ForeignKey(user_table.c.id,
                   ondelete='CASCADE'), nullable=False, unique=True),
        sql.Column('rules', ks_sql.JsonBlob, nullable=False),
        sql.Column('enabled', sql.Boolean, default=True, nullable=False,
                   server_default=sql.sql.expression.true()),
        mysql_engine='InnoDB',
        mysql_charset='utf8')

    user_mfa_rules_table.create(migrate_engine, checkfirst=True)
