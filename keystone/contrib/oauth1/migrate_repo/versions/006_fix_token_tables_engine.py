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

import migrate
import sqlalchemy as sql


def upgrade(migrate_engine):
    if migrate_engine.name != 'mysql':
        return

    meta = sql.MetaData()
    meta.bind = migrate_engine

    consumer_table = sql.Table('consumer', meta, autoload=True)
    request_token_table = sql.Table('request_token', meta, autoload=True)
    access_token_table = sql.Table('access_token', meta, autoload=True)

    if consumer_table.dialect_options['mysql']['engine'] != 'InnoDB':
        migrate_engine.execute("ALTER TABLE consumer Engine=InnoDB")

    if request_token_table.dialect_options['mysql']['engine'] != 'InnoDB':
        migrate_engine.execute("ALTER TABLE request_token Engine=InnoDB")
        migrate.ForeignKeyConstraint(
            columns=[request_token_table.c.consumer_id],
            refcolumns=[consumer_table.c.id],
        ).create()

    if access_token_table.dialect_options['mysql']['engine'] != 'InnoDB':
        migrate_engine.execute("ALTER TABLE access_token Engine=InnoDB")
        migrate.ForeignKeyConstraint(
            columns=[access_token_table.c.consumer_id],
            refcolumns=[consumer_table.c.id],
        ).create()
