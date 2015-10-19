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

DELEGATION_TABLE = 'delegation'
ROLE_DELEGATION_TABLE = 'role_delegation'


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    fake_role = sql.Table(
        'role', meta,
        sql.Column('id', sql.String(length=64), primary_key=True),
        mysql_engine='InnoDB',
        mysql_charset='utf8')

    delegation_table = sql.Table(
        DELEGATION_TABLE,
        meta,
        sql.Column('id', sql.String(64), nullable=False, primary_key=True),
        sql.Column('trustor_id', sql.String(64), nullable=False),
        sql.Column('impersonation', sql.Boolean, nullable=False),
        sql.Column('origins', sql.Text, nullable=False),
        sql.Column('ancestors', sql.Text, nullable=False),
        sql.Column('strict', sql.Boolean, nullable=False),
        sql.Column('transitive', sql.Boolean, nullable=False),
        sql.Column('active', sql.Boolean, nullable=False),
        sql.Column('user_id', sql.String(64)),
        sql.Column('group_id', sql.String(64)),
        sql.Column('project_id', sql.String(64)),
        sql.Column('domain_id', sql.String(64)),
        sql.Column('inherited', sql.Boolean, nullable=False),
        sql.Column('deleted_at', sql.DateTime),
        sql.Column('expires_at', sql.DateTime),
        sql.Column('remaining_uses', sql.Integer),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    delegation_table.create()

    role_delegation_table = sql.Table(
        ROLE_DELEGATION_TABLE,
        meta,
        sql.Column('delegation_id', sql.String(64),
                   sql.ForeignKey(delegation_table.c.id), nullable=False),
        sql.Column('role_id', sql.String(64), sql.ForeignKey(fake_role.c.id),
                   nullable=False),
        sql.PrimaryKeyConstraint('delegation_id', 'role_id'),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    role_delegation_table.create()
