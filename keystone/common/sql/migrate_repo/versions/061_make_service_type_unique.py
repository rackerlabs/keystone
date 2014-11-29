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

"""Make the `type` column on the `service` table unique.

When creating a service, the service's type is a required parameter. This
parameter should also be unique across all services.

To upgrade, create a new `service` table with the unique flag set on the `type`
column. Migrate all data from the existing `service` table to the new table.
Finally, drop the old `service` table and rename the temporary table to be the
`service` table.

Downgrade will follow the same workflow as upgrade, only when we recreate the
`service` table, don't create it with a unique flag on the `type` column.

"""

import migrate
import sqlalchemy as sql
from sqlalchemy.orm import sessionmaker

from keystone.common import sql as ks_sql

_TEMP_SERVICE_TABLE_NAME = 'temp_service'
_SERVICE_TABLE_NAME = 'service'


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    maker = sessionmaker(bind=migrate_engine)
    session = maker()

    # Create a temporary service table that has a unique constraint on `type`
    temp_service_table = sql.Table(
        _TEMP_SERVICE_TABLE_NAME, meta,
        sql.Column('id', sql.String(length=64), primary_key=True),
        sql.Column('type', sql.String(length=255), unique=True),
        sql.Column('enabled', sql.Boolean, nullable=False, default=True,
                   server_default='1'),
        sql.Column('extra', ks_sql.JsonBlob.impl),
        mysql_engine='InnoDB',
        mysql_charset='utf8')

    temp_service_table.create(migrate_engine, checkfirst=True)

    # Migrate data from service table to temp_service table
    service_table = sql.Table(_SERVICE_TABLE_NAME, meta, autoload=True)

    # Grab all existing service entries
    services = list(service_table.select().execute())

    for service in services:
        session.execute(temp_service_table.insert().values(
            id=service.id,
            type=service.type,
            enabled=service.enabled,
            extra=service.extra)
        )

    session.commit()
    session.close()

    # Drop the old service table
    service_table.drop()

    # Rename the temporary service table
    migrate.rename_table(temp_service_table, _SERVICE_TABLE_NAME, meta.bind)


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    maker = sessionmaker(bind=migrate_engine)
    session = maker()

    # Create a service table that doesn't have a unique constraint on `type`
    temp_service_table = sql.Table(
        _TEMP_SERVICE_TABLE_NAME, meta,
        sql.Column('id', sql.String(length=64), primary_key=True),
        sql.Column('type', sql.String(length=255)),
        sql.Column('enabled', sql.Boolean, nullable=False, default=True,
                   server_default='1'),
        sql.Column('extra', ks_sql.JsonBlob.impl),
        mysql_engine='InnoDB',
        mysql_charset='utf8')

    temp_service_table.create(migrate_engine, checkfirst=True)

    # Migrate data from service table to temp_service table
    service_table = sql.Table(_SERVICE_TABLE_NAME, meta, autoload=True)

    services = list(service_table.select().execute())

    for service in services:
        session.execute(temp_service_table.insert().values(
            id=service.id,
            type=service.type,
            enabled=service.enabled,
            extra=service.extra)
        )

    session.commit()
    session.close()

    # Drop the old service table
    service_table.drop()

    # Rename the temporary service table
    migrate.rename_table(temp_service_table, _SERVICE_TABLE_NAME, meta.bind)
