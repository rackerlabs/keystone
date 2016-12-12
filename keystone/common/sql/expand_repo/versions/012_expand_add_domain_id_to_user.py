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
CREATE TRIGGER user_insert_read_only BEFORE INSERT ON user
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = '%s';
END;
"""

SQLITE_INSERT_TRIGGER = """
CREATE TRIGGER user_insert_read_only BEFORE INSERT ON user
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

CREATE TRIGGER user_insert_read_only BEFORE INSERT ON user
FOR EACH ROW
EXECUTE PROCEDURE keystone_read_only_insert();
"""


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    user = sql.Table('user', meta, autoload=True)
    project = sql.Table('project', meta, autoload=True)
    domain_id = sql.Column('domain_id', sql.String(64),
                           sql.ForeignKey(project.c.id), nullable=True)
    user.create_column(domain_id)

    if upgrades.USE_TRIGGERS:
        error_message = ('User migration in process...')
        if migrate_engine.name == 'postgresql':
            user_insert_trigger = POSTGRESQL_INSERT_TRIGGER % error_message
        elif migrate_engine.name == 'sqlite':
            user_insert_trigger = SQLITE_INSERT_TRIGGER % error_message
        else:
            user_insert_trigger = MYSQL_INSERT_TRIGGER % error_message
        migrate_engine.execute(user_insert_trigger)
