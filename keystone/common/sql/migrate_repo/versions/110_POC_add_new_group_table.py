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

    new_groups_table = sql.Table(
        'new_group',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(64), nullable=False),
        sql.Column('domain_id', sql.String(64), nullable=False),
        sql.Column('description', sql.Text),
        sql.Column('extra', ks_sql.JsonBlob.impl),
        mysql_engine='InnoDB',
        mysql_charset='utf8')
    new_groups_table.create(migrate_engine, checkfirst=True)

    # Weirdly, the name of the existing group table appears to be "group"
    # including the quotes!! This appears to be only true from the group
    # table, not other tables.

    stmnt = 'CREATE TRIGGER new_group_to_group AFTER INSERT ON new_group '
    stmnt += 'BEGIN INSERT OR IGNORE INTO "group" (id, name, domain_id, '
    stmnt += 'description, extra) VALUES (new.id, new.name, new.domain_id, '
    stmnt += 'new.description, new.extra); END;'
    migrate_engine.execute(stmnt)

    stmnt = 'CREATE TRIGGER group_to_new_group AFTER INSERT ON "group" '
    stmnt += 'BEGIN INSERT OR IGNORE INTO new_group (id, name, domain_id, '
    stmnt += 'description, extra) VALUES (new.id, new.name, new.domain_id, '
    stmnt += 'new.description, new.extra); END;'
    migrate_engine.execute(stmnt)
