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

from keystone.common.sql import upgrades


MYSQL_INSERT_TRIGGER = """
CREATE TRIGGER %s_insert_trigger
AFTER INSERT
    ON %s FOR EACH ROW
BEGIN
    UPDATE %s SET %s_id = (
        SELECT id FROM %s WHERE id = NEW.id)
        WHERE id = NEW.id and %s_id IS NULL;
END;
"""

SQLITE_INSERT_TRIGGER = """
CREATE TRIGGER %s_insert_trigger
AFTER INSERT
    ON %s
BEGIN
    UPDATE %s SET %s_id = (
        SELECT id FROM %s WHERE id = NEW.id)
        WHERE id = NEW.id and %s_id IS NULL;
END;
"""

POSTGRESQL_INSERT_TRIGGER = """
CREATE OR REPLACE FUNCTION update_%s_id()
    RETURNS trigger AS
$BODY$
BEGIN
    UPDATE "%s" SET %s_id = (
        SELECT id FROM %s WHERE id = NEW.id)
        WHERE id = NEW.id and %s_id IS NULL;
    RETURN NULL;
END
$BODY$ LANGUAGE plpgsql;

CREATE TRIGGER %s_insert_trigger AFTER INSERT ON %s
FOR EACH ROW
EXECUTE PROCEDURE update_%s_id();
"""


def upgrade(migrate_engine):

    meta = sql.MetaData()
    meta.bind = migrate_engine

    registered_limit_table = sql.Table(
        'registered_limit', meta, autoload=True
    )
    registered_limit_id = sql.Column('registered_limit_id',
                                     sql.String(length=64))
    registered_limit_new_id = sql.Column('new_id', sql.Integer,
                                         primary_key=True)
    registered_limit_table.create_column(registered_limit_id)
    registered_limit_table.create_column(registered_limit_new_id)

    limit_table = sql.Table('limit', meta, autoload=True)
    limit_id = sql.Column('limit_id', sql.String(length=64))
    limit_new_id = sql.Column('new_id', sql.Integer, primary_key=True)
    limit_table.create_column(limit_id)
    limit_table.create_column(limit_new_id)

    if upgrades.USE_TRIGGERS:
        if migrate_engine.name == 'postgresql':
            registered_limit_insert_trigger = (POSTGRESQL_INSERT_TRIGGER %
                                               "registered_limit")
            limit_insert_trigger = POSTGRESQL_INSERT_TRIGGER % "limit"
        elif migrate_engine.name == 'sqlite':
            registered_limit_insert_trigger = (SQLITE_INSERT_TRIGGER %
                                               "registered_limit")
            limit_insert_trigger = SQLITE_INSERT_TRIGGER % "limit"
        else:
            registered_limit_insert_trigger = (MYSQL_INSERT_TRIGGER %
                                               "registered_limit")
            limit_insert_trigger = MYSQL_INSERT_TRIGGER % "limit"
        migrate_engine.execute(registered_limit_insert_trigger)
        migrate_engine.execute(limit_insert_trigger)
