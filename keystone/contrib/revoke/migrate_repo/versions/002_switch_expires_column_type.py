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
from sqlalchemy.orm import sessionmaker

from keystone.common import sql as ks_sql


_TABLE_NAME = 'revocation_events'


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    if migrate_engine.name == 'mysql':
        events_table = sql.Table(_TABLE_NAME, meta, autoload=True)
        new_expires_at = sql.Column('_expires_at_tmp',
                                    ks_sql.ISOStringDatetime(26),
                                    nullable=True)
        events_table.create_column(new_expires_at)

        session = sessionmaker(bind=migrate_engine)()
        for event in session.query(events_table):
            event._expires_at_tmp = event.expires_at

        session.commit()
        session.close()

        events_table.c.expires_at.drop()
        events_table.c._expires_at.alter(name='expires_at')


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    if migrate_engine.name == 'mysql':
        events_table = sql.Table(_TABLE_NAME, meta, autoload=True)
        new_expires_at = sql.Column('_expires_at_tmp',
                                    sql.DateTime(),
                                    nullable=True)
        events_table.create_column(new_expires_at)

        session = sessionmaker(bind=migrate_engine)()
        for event in session.query(events_table):
            event._expires_at_tmp = event.expires_at

        session.commit()
        session.close()

        events_table.c.expires_at.drop()
        events_table.c._expires_at.alter(name='expires_at')
