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

from keystone.common import sql as ks_sql


def upgrade(migrate_engine):

    meta = sql.MetaData()
    meta.bind = migrate_engine

    application_credentials_table = sql.Table(
        'application_credential', meta,
        sql.Column('id', sql.String(length=64), primary_key=True),
        sql.Column('name', sql.String(length=255), nullable=False),
        sql.Column('secret_hash', sql.String(length=255), nullable=False),
        sql.Column('description', sql.Text),
        sql.Column('user_id', sql.String(length=64), nullable=False),
        sql.Column('project_id', sql.String(64), nullable=False),
        sql.Column('trust_id', sql.String(length=64)),
        sql.Column('expires_at', ks_sql.DateTimeInt(),
                   nullable=True),
        sql.UniqueConstraint('user_id', 'name',
                             name='duplicate_app_cred_constraint'),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    application_credentials_table.create(migrate_engine, checkfirst=True)
