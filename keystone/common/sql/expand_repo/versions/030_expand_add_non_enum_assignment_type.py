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

from keystone.common.sql import upgrades


# NOTE(lbragstad): MySQL error state of 45000 is a generic unhandled exception.
# Keystone will return a 500 in this case.
MYSQL_INSERT_TRIGGER = """
CREATE TRIGGER assignment_insert_read_only BEFORE INSERT ON assignment
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = '%s';
END;
"""

MYSQL_UPDATE_TRIGGER = """
CREATE TRIGGER assignment_update_read_only BEFORE UPDATE ON assignment
FOR EACH ROW
BEGIN
  IF NEW.assignment_type IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '%s';
  END IF;
  IF NEW.assignment_type IS NOT NULL AND OLD.type IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '%s';
  END IF;
END;
"""

SQLITE_INSERT_TRIGGER = """
CREATE TRIGGER assignment_insert_read_only BEFORE INSERT ON assignment
BEGIN
  SELECT RAISE (ABORT, '%s');
END;
"""

SQLITE_UPDATE_TRIGGER = """
CREATE TRIGGER assignment_update_read_only BEFORE UPDATE ON assignment
WHEN NEW.assignment_type IS NULL
BEGIN
  SELECT RAISE (ABORT, '%s');
END;
"""

POSTGRESQL_INSERT_TRIGGER = """
CREATE OR REPLACE FUNCTION keystone_read_only_insert()
  RETURNS trigger AS
$BODY$
BEGIN
  RAISE EXCEPTION '%s';
END
$BODY$ LANGUAGE plpgsql;

CREATE TRIGGER assignment_insert_read_only BEFORE INSERT ON assignment
FOR EACH ROW
EXECUTE PROCEDURE keystone_read_only_insert();
"""

POSTGRESQL_UPDATE_TRIGGER = """
CREATE OR REPLACE FUNCTION keystone_read_only_update()
  RETURNS trigger AS
$BODY$
BEGIN
  IF NEW.assignment_type IS NULL THEN
    RAISE EXCEPTION '%s';
  END IF;
  IF NEW.assignment_type IS NOT NULL AND OLD.type IS NULL THEN
    RAISE EXCEPTION '%s';
  END IF;
  RETURN NEW;
END
$BODY$ LANGUAGE plpgsql;

CREATE TRIGGER assignment_update_read_only BEFORE UPDATE ON assignment
FOR EACH ROW
EXECUTE PROCEDURE keystone_read_only_update();
"""


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    # Approach 4b from
    # https://etherpad.openstack.org/p/keystone-non-enum-migration
    assignment_table_name = 'assignment'
    assignment_table = sql.Table(assignment_table_name, meta, autoload=True)

    # Expand the database to include a new column called `assignment_type`
    # which is a nullable VARCHAR(64)
    assignment_type = sql.Column(
        'assignment_type', sql.String(64), nullable=True, primary_key=True
    )
    assignment_table.create_column(assignment_type)

    if not upgrades.USE_TRIGGERS:
        # Don't handle the database triggers unless we're dealing with an
        # online migration.
        return

    # Create triggers to make the assignment table read-only
    error_message = ('Assignment migration in progress. Cannot perform '
                     'writes to assignment table.')
    if migrate_engine.name == 'postgresql':
        assignment_insert_trigger = POSTGRESQL_INSERT_TRIGGER % error_message
        assignment_update_trigger = POSTGRESQL_UPDATE_TRIGGER % (
            error_message, error_message
        )
    elif migrate_engine.name == 'sqlite':
        assignment_insert_trigger = SQLITE_INSERT_TRIGGER % error_message
        assignment_update_trigger = SQLITE_UPDATE_TRIGGER % error_message
    else:
        assignment_insert_trigger = MYSQL_INSERT_TRIGGER % error_message
        assignment_update_trigger = MYSQL_UPDATE_TRIGGER % (
            error_message, error_message
        )

    migrate_engine.execute(assignment_insert_trigger)
    migrate_engine.execute(assignment_update_trigger)
