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

from keystone.common.sql import upgrades


REG_LIMIT_MYSQL_INSERT_TRIGGER = """
CREATE TRIGGER registered_limit_insert_trigger
AFTER INSERT
    ON `registered_limit` FOR EACH ROW
BEGIN
    INSERT INTO `registered_limit_new`(registered_limit_id, service_id,
    region_id, resource_name, default_limit) VALUES(NEW.id, NEW.service_id,
    NEW.region_id, NEW.resource_name, NEW.default_limit)
END;
"""

LIMIT_MYSQL_INSERT_TRIGGER = """
CREATE TRIGGER limit_insert_trigger
AFTER INSERT
    ON `limit` FOR EACH ROW
BEGIN
    INSERT INTO `limit_new`(limit_id, service_id, region_id, project_id,
    resource_name, resource_limit) VALUES(NEW.id, NEW.service_id,
    NEW.region_id, NEW.project_id, NEW.resource_name, NEW.resource_limit)
END;
"""

REG_LIMIT_SQLITE_INSERT_TRIGGER = """
CREATE TRIGGER registered_limit_insert_trigger
AFTER INSERT
    ON `registered_limit`
BEGIN
    INSERT INTO `registered_limit_new`(registered_limit_id, service_id,
    region_id, resource_name, default_limit) VALUES(NEW.id, NEW.service_id,
    NEW.region_id, NEW.resource_name, NEW.default_limit)
END;
"""

LIMIT_SQLITE_INSERT_TRIGGER = """
CREATE TRIGGER limit_insert_trigger
AFTER INSERT
    ON `limit`
BEGIN
    INSERT INTO `limit_new`(limit_id, service_id, region_id, project_id,
    resource_name, resource_limit) VALUES(NEW.id, NEW.service_id,
    NEW.region_id, NEW.project_id, NEW.resource_name, NEW.resource_limit)
END;
"""

REG_LIMIT_POSTGRESQL_INSERT_TRIGGER = """
CREATE OR REPLACE FUNCTION update_registered_limit_id()
    RETURNS trigger AS
$BODY$
BEGIN
    INSERT INTO `registered_limit_new`(registered_limit_id, service_id,
    region_id, resource_name, default_limit) VALUES(NEW.id, NEW.service_id,
    NEW.region_id, NEW.resource_name, NEW.default_limit)
END
$BODY$ LANGUAGE plpgsql;

CREATE TRIGGER registered_limit_insert_trigger AFTER INSERT ON registered_limit
FOR EACH ROW
EXECUTE PROCEDURE update_registered_limit_id();
"""

LIMIT_POSTGRESQL_INSERT_TRIGGER = """
CREATE OR REPLACE FUNCTION update_limit_id()
    RETURNS trigger AS
$BODY$
BEGIN
    INSERT INTO `limit_new`(limit_id, service_id, region_id, project_id,
    resource_name, resource_limit) VALUES(NEW.id, NEW.service_id,
    NEW.region_id, NEW.project_id, NEW.resource_name, NEW.resource_limit)
END
$BODY$ LANGUAGE plpgsql;

CREATE TRIGGER limit_insert_trigger AFTER INSERT ON `limit`
FOR EACH ROW
EXECUTE PROCEDURE update_limit_id();
"""


def upgrade(migrate_engine):

    meta = sql.MetaData()
    meta.bind = migrate_engine

    registered_limit_table_new = sql.Table(
        'registered_limit_new',
        meta,
        sql.Column('id', sql.Integer, primary_key=True),
        sql.Column('registered_limit_id', sql.String(length=64)),
        sql.Column('service_id', sql.String(64)),
        sql.Column('region_id', sql.String(64), nullable=True),
        sql.Column('resource_name', sql.String(255)),
        sql.Column('default_limit', sql.Integer, nullable=False),
        sql.UniqueConstraint('service_id', 'region_id', 'resource_name'),
        mysql_engine='InnoDB',
        mysql_charset='utf8')
    registered_limit_table_new.create(migrate_engine, checkfirst=True)

    limit_table_new = sql.Table(
        'limit_new',
        meta,
        sql.Column('id', sql.Integer, primary_key=True),
        sql.Column('limit_id', sql.String(length=64)),
        sql.Column('project_id', sql.String(64)),
        sql.Column('service_id', sql.String(64)),
        sql.Column('region_id', sql.String(64), nullable=True),
        sql.Column('resource_name', sql.String(255)),
        sql.Column('resource_limit', sql.Integer, nullable=False),
        sql.UniqueConstraint('project_id', 'service_id', 'region_id',
                             'resource_name'),
        mysql_engine='InnoDB',
        mysql_charset='utf8')
    limit_table_new.create(migrate_engine, checkfirst=True)

    migrate.ForeignKeyConstraint(
        columns=[limit_table_new.c.service_id,
                 limit_table_new.c.region_id,
                 limit_table_new.c.resource_name],
        refcolumns=[registered_limit_table_new.c.service_id,
                    registered_limit_table_new.c.region_id,
                    registered_limit_table_new.c.resource_name]).create()

    if upgrades.USE_TRIGGERS:
        if migrate_engine.name == 'postgresql':
            registered_limit_insert_trigger = (
                REG_LIMIT_POSTGRESQL_INSERT_TRIGGER)
            limit_insert_trigger = LIMIT_POSTGRESQL_INSERT_TRIGGER
        elif migrate_engine.name == 'sqlite':
            registered_limit_insert_trigger = REG_LIMIT_SQLITE_INSERT_TRIGGER
            limit_insert_trigger = LIMIT_SQLITE_INSERT_TRIGGER
        else:
            registered_limit_insert_trigger = REG_LIMIT_MYSQL_INSERT_TRIGGER
            limit_insert_trigger = LIMIT_MYSQL_INSERT_TRIGGER
        migrate_engine.execute(registered_limit_insert_trigger)
        migrate_engine.execute(limit_insert_trigger)
