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

# A null initial migration to open this repo. Do not re-use replace this with
# a real migration, add additional ones in subsequent version scripts.

import datetime

import sqlalchemy as sql

from keystone.common.sql import migration_helpers


MYSQL_INSERT_TRIGGER = """
CREATE TRIGGER password_created_at_new BEFORE INSERT ON password
FOR EACH ROW
BEGIN
  SET NEW.created_at_new = UTC_TIMESTAMP();
END;
"""

SQLITE_INSERT_TRIGGER = """
CREATE TRIGGER password_created_at_new AFTER INSERT ON password
BEGIN
  UPDATE password SET created_at_new = DATETIME('now') WHERE id = NEW.id;
END;
"""

POSTGRESQL_INSERT_TRIGGER = """
CREATE OR REPLACE FUNCTION password_created_at_new_insert()
  RETURNS trigger AS
$BODY$
BEGIN
  NEW.created_at_new := now() at time zone 'UTC';
END
$BODY$ LANGUAGE plpgsql;

CREATE TRIGGER password_created_at_new BEFORE INSERT ON password
FOR EACH ROW
EXECUTE PROCEDURE password_created_at_new_insert();
"""


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    # add new created_at column
    password = sql.Table('password', meta, autoload=True)
    created_at_new = sql.Column('created_at_new', sql.DateTime(),
                                nullable=True,
                                default=datetime.datetime.utcnow)
    password.create_column(created_at_new)
    # add triggers
    if migration_helpers.USE_TRIGGERS:
        if migrate_engine.name == 'postgresql':
            insert_trigger = POSTGRESQL_INSERT_TRIGGER
        elif migrate_engine.name == 'sqlite':
            insert_trigger = SQLITE_INSERT_TRIGGER
        else:
            insert_trigger = MYSQL_INSERT_TRIGGER
        migrate_engine.execute(insert_trigger)
