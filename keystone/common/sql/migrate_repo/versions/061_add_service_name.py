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


"""Adds a `name` column to the `service` table.

The `name` attribute for each service was previously stored in the `extra`
column of the `service` table.

To upgrade, the `name` column is added and will be populated with the `name`
attribute stored in the `extra` column.

To downgrade, the `name` attribute stored in the `name` column will be injected
into the `extra` column and the `name` column removed from the `service` table.

"""

from oslo.serialization import jsonutils
from oslo.utils import strutils
import sqlalchemy as sql
from sqlalchemy.orm import sessionmaker


def _migrate_name_from_extra(migrate_engine, service_table):
    """Remove `name` from `extra` and put it in the `name` column."""

    services = list(service_table.select().execute())

    for service in services:
        extra_dict = jsonutils.loads(service.extra)

        # what to do if service['name'] doesn't exist?

        service_name = extra_dict.pop('name')

        new_values = {
            'name': service_name,
            'extra': jsonutils.dumps(extra_dict),
        }
        f = service_table.c.id == service.id
        update = service_table.update().where(f).values(new_values)
        migrate_engine.execute(update)


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    service_table = sql.Table('service', meta, autoload=True)
    name_column = sql.Column('name', sql.String(length=255), nullable=True)
    name_column.create(service_table)

    _migrate_name_from_extra(migrate_engine, service_table)


def _migrate_name_to_extra(migrate_engine, service_table):
    """Get `name` value from `name` column and put it in `extra` JSON."""

    services = list(service_table.select().execute())

    for service in services:

        service_name = service.name

        extra_dict = jsonutils.loads(service.extra)
        extra_dict['name'] = service_name

        new_values = {
            'extra': jsonutils.dumps(extra_dict),
        }
        f = service_table.c.id == service.id
        update = service_table.update().where(f).values(new_values)
        migrate_engine.execute(update)


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    service_table = sql.Table('service', meta, autoload=True)
    _migrate_name_to_extra(migrate_engine, service_table)

    if migrate_engine.name == 'sqlite':
        meta.clear()
        _downgrade_service_table_with_copy(meta, migrate_engine)
        return

    service_table.c.name.drop()
