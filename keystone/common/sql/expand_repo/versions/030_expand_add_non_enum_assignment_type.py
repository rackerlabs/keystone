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


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    assignment_table = sql.Table('assignment', meta, autoload=True)
    ACTOR_ID_INDEX_NAME = 'ix_actor_id'
    TMP_ASSIGNMENT_TABLE_NAME = 'tmp_assignment'
    tmp_assignment_table = sql.Table(
        TMP_ASSIGNMENT_TABLE_NAME, meta,
        sql.Column('assignment_type', sql.String(64), nullable=False),
        sql.Column('actor_id', sql.String(64), nullable=False),
        sql.Column('target_id', sql.String(64), nullable=False),
        sql.Column('role_id', sql.String(64), sql.ForeignKey('role.id'),
                   nullable=False),
        sql.Column('inherited', sql.Boolean, default=False, nullable=False),
        sql.PrimaryKeyConstraint('assignment_type', 'actor_id', 'target_id',
                                 'role_id', 'inherited'),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )
    tmp_assignment_table.create(migrate_engine, checkfirst=True)
    sql.Index(ACTOR_ID_INDEX_NAME, assignment_table.c.actor_id).drop()
    sql.Index(ACTOR_ID_INDEX_NAME, tmp_assignment_table.c.actor_id).create()
