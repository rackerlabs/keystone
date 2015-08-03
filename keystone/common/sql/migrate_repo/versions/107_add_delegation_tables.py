# Copyright 2016 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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
import migrate
import sqlalchemy as sql


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    delegation_table = sql.Table(
        'delegation',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('trustor_id', sql.String(64)),
        sql.Column('agent_id', sql.String(64)),
        sql.Column('impersonation', sql.Boolean,
                   nullable=False, default=False),
        sql.Column('redelegated_id', sql.String(64)),
        sql.Column('strict_ancestry', sql.Boolean,
                   nullable=False, default=False),
        sql.Column('sealed', sql.Boolean, nullable=False, default=True),
        sql.Column('executable', sql.Boolean, nullable=False, default=True),
        sql.Column('inherited_to_projects', sql.Boolean, nullable=False,
                   default=False),
        sql.Column('user_id', sql.String(64)),
        sql.Column('group_id', sql.String(64)),
        sql.Column('project_id', sql.String(64)),
        sql.Column('domain_id', sql.String(64)),
        sql.Column('deleted_at', sql.DateTime),
        sql.Column('expires_at', sql.DateTime),
        sql.Column('remaining_uses', sql.Integer),
        sql.Column('redelegation_count', sql.Integer),
        sql.Column('extra', sql.Text()),

        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    delegation_table.create(migrate_engine, checkfirst=True)

    migrate.UniqueConstraint(
        delegation_table.c.trustor_id,
        delegation_table.c.user_id,
        delegation_table.c.project_id,
        delegation_table.c.impersonation,
        delegation_table.c.expires_at,
        name='unique_delegation_constraint'
    ).create()

    role_table = sql.Table('role', meta, autoload=True)

    role_delegation_table = sql.Table(
        'role_delegation',
        meta,
        sql.Column('id', sql.Integer, primary_key=True),
        sql.Column('delegation_id', sql.String(64),
                   sql.ForeignKey(delegation_table.c.id,
                                  ondelete="CASCADE", onupdate="CASCADE"),
                   nullable=False),
        sql.Column('role_id', sql.String(64),
                   sql.ForeignKey(role_table.c.id,
                                  ondelete="CASCADE", onupdate="CASCADE"),
                   nullable=False),

        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    role_delegation_table.create(migrate_engine, checkfirst=True)

    migrate.UniqueConstraint(
        role_delegation_table.c.role_id,
        role_delegation_table.c.delegation_id,
        name='unique_role_delegation_constraint'
    ).create()
