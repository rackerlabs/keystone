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
CREATE TRIGGER user_after_insert_update_domain_id
AFTER INSERT
    ON user FOR EACH ROW
BEGIN
    IF (NEW.domain_id IS NULL) THEN
        IF (SELECT 1 = 1 FROM local_user WHERE user_id=NEW.id) THEN
            UPDATE user SET domain_id = (
                SELECT domain_id FROM local_user WHERE user_id=NEW.id);
        ELSEIF (SELECT 1 = 1 FROM nonlocal_user WHERE user_id=NEW.id) THEN
            UPDATE user SET domain_id = (
                SELECT domain_id FROM nonlocal_user WHERE user_id=NEW.id);
        END IF;
    END IF;
END;
"""

SQLITE_INSERT_TRIGGER = """
CREATE TRIGGER user_after_insert_update_domain_id
AFTER INSERT
    ON user
BEGIN
    UPDATE user SET domain_id = (
        SELECT domain_id FROM local_user WHERE user_id=NEW.id)
        WHERE NEW.domain_id IS NULL AND EXISTS(
            SELECT 1 FROM local_user WHERE user_id=NEW.id);
    UPDATE user SET domain_id = (
        SELECT domain_id FROM nonlocal_user WHERE user_id=NEW.id)
        WHERE NEW.domain_id IS NULL AND EXISTS(
            SELECT 1 FROM nonlocal_user WHERE user_id=NEW.id);
END;
"""

POSTGRESQL_INSERT_TRIGGER = """
CREATE OR REPLACE FUNCTION update_user_domain_id()
    RETURNS trigger AS
$BODY$
BEGIN
    IF (NEW.domain_id IS NULL) THEN
        IF EXISTS (SELECT 1 FROM local_user WHERE user_id=NEW.id) THEN
            UPDATE user SET domain_id = (
                SELECT domain_id FROM local_user WHERE user_id=NEW.id);
        ELSIF EXISTS (SELECT 1 FROM nonlocal_user WHERE user_id=NEW.id) THEN
            UPDATE user SET domain_id = (
                SELECT domain_id FROM nonlocal_user WHERE user_id=NEW.id);
        END IF;
    END IF;
END
$BODY$ LANGUAGE plpgsql;

CREATE TRIGGER user_after_insert_update_domain_id
AFTER INSERT
    ON user FOR EACH ROW
EXECUTE PROCEDURE update_user_domain_id();
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
        if migrate_engine.name == 'postgresql':
            user_insert_trigger = POSTGRESQL_INSERT_TRIGGER
        elif migrate_engine.name == 'sqlite':
            user_insert_trigger = SQLITE_INSERT_TRIGGER
        else:
            user_insert_trigger = MYSQL_INSERT_TRIGGER
        migrate_engine.execute(user_insert_trigger)
