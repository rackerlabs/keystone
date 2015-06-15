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

CONFIG_MUTEX_TABLE = 'config_mutex'


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    # Since the creation of the mutex table will be backported, we allow for
    # the fact that the table may or may not have already been created (since
    # we can't guarantee a given installation installed the backported code).

    try:
        sql.Table(CONFIG_MUTEX_TABLE, meta, autoload=True)
    except sql.exc.NoSuchTableError:
        mutex_table = sql.Table(
            CONFIG_MUTEX_TABLE,
            meta,
            sql.Column('mutex', sql.String(64), primary_key=True),
            sql.Column('domain_id', sql.String(64), nullable=False),
            mysql_engine='InnoDB',
            mysql_charset='utf8')
        mutex_table.create(migrate_engine, checkfirst=True)
