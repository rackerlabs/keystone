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


MYSQL_INSERT_TRIGGER = """
DELIMITER $$
CREATE TRIGGER credential_insert_read_only BEFORE INSERT ON credential
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '%d'
    SET MESSAGE_TEXT = '%s', MYSQL_ERRNO = %d;
END; $$
DELIMITER ;
"""

MYSQL_UPDATE_TRIGGER = """
DELIMITER $$
CREATE TRIGGER credential_update_read_only BEFORE UPDATE ON credential
FOR EACH ROW
BEGIN
  IF (NEW.encrypted_blob IS NULL AND OLD.encrypted_blob IS NULL) OR
     (NEW.blob IS NULL AND OLD.blob IS NULL) THEN
    SIGNAL SQLSTATE '%d' SET MESSAGE_TEXT = '%s', MYSQL_ERRNO = '%d';
  END IF;
END; $$
DELIMITER ;
"""

SQLITE_INSERT_TRIGGER = """
CREATE TRIGGER credential_insert_read_only BEFORE INSERT ON credential
BEGIN
  SELECT RAISE (ABORT, '%s');
END;
"""

SQLITE_UPDATE_TRIGGER = """
CREATE TRIGGER credential_update_read_only BEFORE UPDATE ON credential
WHEN NEW.encrypted_blob IS NULL
BEGIN
  SELECT RAISE (ABORT, '%s');
END;
"""

# This still needs to be fixed.
POSTGRESQL_INSERT_TRIGGER = """
CREATE OR REPLACE FUNCTION read_only()
  RETURNS trigger AS
$BODY$
BEGIN
  RAISE EXCEPTION '%s';
END
$BODY$ LANGUAGE plpgsql;

CREATE TRIGGER credential_read_only BEFORE INSERT ON credential
FOR EACH ROW
EXECUTE PROCEDURE read_only();
"""

# This still needs to be fixed.
POSTGRESQL_UPDATE_TRIGGER = """
CREATE OR REPLACE FUNCTION read_only()
  RETURNS trigger AS
$BODY$
BEGIN
  RAISE EXCEPTION '%s';
END
$BODY$ LANGUAGE plpgsql;

CREATE TRIGGER credential_read_only BEFORE INSERT ON credential
FOR EACH ROW
EXECUTE PROCEDURE read_only();
"""


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    key_hash = sql.Column('key_hash', sql.String(7), nullable=True)
    encrypted_blob = sql.Column(
        'encrypted_blob',
        ks_sql.JsonBlob,
        nullable=True
    )
    credential_table = sql.Table('credential', meta, autoload=True)
    credential_table.create_column(key_hash)
    credential_table.create_column(encrypted_blob)

    error_message = ('Credential migration in progress. Cannot perform '
                     'writes to credential table.')
    if migrate_engine.name == 'postgresql':
        credential_insert_trigger = POSTGRESQL_INSERT_TRIGGER % error_message
        credential_update_trigger = POSTGRESQL_UPDATE_TRIGGER % error_message
    elif migrate_engine.name == 'sqlite':
        credential_insert_trigger = SQLITE_INSERT_TRIGGER % error_message
        credential_update_trigger = SQLITE_UPDATE_TRIGGER % error_message
    else:
        error_state = 45000
        mysql_errno = 1001
        credential_insert_trigger = MYSQL_INSERT_TRIGGER % (
            error_state, error_message, mysql_errno
        )
        credential_update_trigger = MYSQL_UPDATE_TRIGGER % (
            error_state, error_message, mysql_errno
        )

    migrate_engine.execute(credential_insert_trigger)
    migrate_engine.execute(credential_update_trigger)
