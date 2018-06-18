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

from migrate import changeset
import sqlalchemy as sql

from keystone.common.sql import upgrades


MYSQL_INSERT_TRIGGER = """
CREATE TRIGGER %(table)s_insert_trigger
AFTER INSERT
    ON `%(table)s` FOR EACH ROW
BEGIN
    UPDATE `%(table)s` SET %(table)s_id = (
        SELECT id FROM `%(table)s` WHERE id = NEW.id)
        WHERE id = NEW.id and %(table)s_id IS NULL;
END;
"""

SQLITE_INSERT_TRIGGER = """
CREATE TRIGGER %(table)s_insert_trigger
AFTER INSERT
    ON `%(table)s`
BEGIN
    UPDATE `%(table)s` SET %(table)s_id = (
        SELECT id FROM `%(table)s` WHERE id = NEW.id)
        WHERE id = NEW.id and %(table)s_id IS NULL;
END;
"""

POSTGRESQL_INSERT_TRIGGER = """
CREATE OR REPLACE FUNCTION update_%(table)s_id()
    RETURNS trigger AS
$BODY$
BEGIN
    UPDATE "%(table)s" SET %(table)s_id = (
        SELECT id FROM %(table)s WHERE id = NEW.id)
        WHERE id = NEW.id and %(table)s_id IS NULL;
    RETURN NULL;
END
$BODY$ LANGUAGE plpgsql;

CREATE TRIGGER %(table)s_insert_trigger AFTER INSERT ON %(table)s
FOR EACH ROW
EXECUTE PROCEDURE update_%(table)s_id();
"""

CREATE_ID_PRIMARY_KEY_COLUMN = """
ALTER TABLE `%s` ADD `new_id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY;
"""


def upgrade(migrate_engine):

    # For both registered_limit and limit table:
    # 1. drop the primary key for id.
    # 2. add a new column to save unified limit UUID.
    # 3. add a auto increment column for primary key.
    # 4. add the triggers to migrate the data from id column to the new column.

    meta = sql.MetaData()
    meta.bind = migrate_engine

    registered_limit_table = sql.Table('registered_limit', meta, autoload=True)
    pk = changeset.PrimaryKeyConstraint('id', table=registered_limit_table)
    pk.drop()
    registered_limit_id = sql.Column('registered_limit_id',
                                     sql.String(length=64))
    registered_limit_table.create_column(registered_limit_id)
    migrate_engine.execute(CREATE_ID_PRIMARY_KEY_COLUMN % "registered_limit")

    limit_table = sql.Table('limit', meta, autoload=True)
    pk = changeset.PrimaryKeyConstraint('id', table=limit_table)
    pk.drop()
    limit_id = sql.Column('limit_id', sql.String(length=64))
    limit_table.create_column(limit_id)
    migrate_engine.execute(CREATE_ID_PRIMARY_KEY_COLUMN % "limit")

    if upgrades.USE_TRIGGERS:
        if migrate_engine.name == 'postgresql':
            registered_limit_insert_trigger = (
                    POSTGRESQL_INSERT_TRIGGER % {"table": "registered_limit"})
            limit_insert_trigger = POSTGRESQL_INSERT_TRIGGER % {
                "table": "limit"}
        elif migrate_engine.name == 'sqlite':
            registered_limit_insert_trigger = (
                    SQLITE_INSERT_TRIGGER % {"table": "registered_limit"})
            limit_insert_trigger = SQLITE_INSERT_TRIGGER % {"table": "limit"}
        else:
            registered_limit_insert_trigger = (
                    MYSQL_INSERT_TRIGGER % {"table": "registered_limit"})
            limit_insert_trigger = MYSQL_INSERT_TRIGGER % {"table": "limit"}
        migrate_engine.execute(registered_limit_insert_trigger)
        migrate_engine.execute(limit_insert_trigger)
