# Copyright 2014 IBM Corp.
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

    identity_table = sql.Table(
        'identity',
        meta,
        sql.Column('identity_id', sql.String(64), primary_key=True,
                   nullable=False),
        sql.Column('extra', sql.Text(), nullable=True),
        sql.Column('enabled', sql.Boolean, nullable=False, default=True),
        sql.Column('default_project_id', sql.String(64), nullable=True))
    identity_table.create(migrate_engine, checkfirst=True)

    password_table = sql.Table(
        'password',
        meta,
        sql.Column('password_id', sql.String(64), primary_key=True,
                   nullable=False),
        sql.Column('identity_id', sql.String(64),
                   sql.ForeignKey('identity.identity_id', ondelete='CASCADE')),
        sql.Column('user_name', sql.String(255), nullable=False),
        sql.Column('namespace', sql.String(64), nullable=False),
        sql.Column('password', sql.String(256), nullable=False),
        sql.Column('expires_at', sql.DateTime(), nullable=True))
    password_table.create(migrate_engine, checkfirst=True)

    federated_table = sql.Table(
        'federated_identity',
        meta,
        sql.Column('federated_id', sql.String(64), primary_key=True,
                   nullable=False),
        sql.Column('identity_id', sql.String(64),
                   sql.ForeignKey('identity.identity_id', ondelete='CASCADE')),
        sql.Column('protocol_id', sql.String(64), nullable=False),
        sql.Column('unique_id', sql.String(255), nullable=False),
        sql.Column('display_name', sql.String(255), nullable=True))
    federated_table.create(migrate_engine, checkfirst=True)


def downgrade(migrate_engine):
    pass
