# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
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

    assignment_table = sql.Table(
        'assignment',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('type', sql.String(64), nullable=False),
        sql.Column('actor_id', sql.String(64), nullable=False),
        sql.Column('target_id', sql.String(64), nullable=False),
        sql.Column('role_id', sql.String(64), nullable=False),
        sql.Column('inherited', sql.Boolean, nullable=False, default=True),
        sql.UniqueConstraint('type', 'actor_id', 'target_id', 'role_id',
                             'inherited'))
    assignment_table.create(migrate_engine, checkfirst=True)


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    assignment = sql.Table('assignment', meta, autoload=True)
    assignment.drop(migrate_engine, checkfirst=True)
