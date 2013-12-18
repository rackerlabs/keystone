# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
#
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

import json
from keystone import exception
import sqlalchemy as sql
from sqlalchemy.orm import sessionmaker


def migrate_name_from_extra_json_to_name(meta, migrate_engine):
    service_table = sql.Table('service', meta, autoload=True)

    service_list = list(service_table.select().execute())
    session = sessionmaker(bind=migrate_engine)()
    for service in service_list:
        try:
            data = json.loads(service.extra)
            service_name = data.pop('name', None)
        except (ValueError, TypeError):
            # Somehow we have non-json data here.  This
            # is a broken service, but it was broken beforehand.
            # Cleaning it up is not in the scope of this migration.
            continue

        values = {}
        if service_name is not None:
            values['name'] = service_name

        values['extra'] = json.dumps(data)
        update = service_table.update().where(
            service_table.c.id == service['id']).values(values)
        try:
            migrate_engine.execute(update)
        except sql.exc.IntegrityError:
            msg = _('Service name %(name)s already exists')
            message = msg % {'name': service_name}
            raise exception.Conflict(type='service', details=message)

    session.commit()
    session.close()


def migrate_name_from_name_to_extra_json(meta, migrate_engine):
    service_table = sql.Table('service', meta, autoload=True)

    service_list = list(service_table.select().execute())
    session = sessionmaker(bind=migrate_engine)()
    for service in service_list:
        try:
            data = json.loads(service.extra)
        except (ValueError, TypeError):
            # Somehow we have non-json data here.  This
            # is a broken service, but it was broken beforehand.
            # Cleaning it up is not in the scope of this migration.
            continue

        if service.name is not None:
            data['name'] = service.name
            values = {'extra': json.dumps(data)}
            update = service_table.update().where(
                service_table.c.id == service.id).values(values)
            migrate_engine.execute(update)

    session.commit()
    session.close()


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    service_table = sql.Table('service', meta, autoload=True)
    service_name = sql.Column('name', sql.String(64))
    service_table.create_column(service_name, unique_name='name')
    try:
        migrate_name_from_extra_json_to_name(meta, migrate_engine)
    except exception.Conflict:
        # During a conflict, restore the extra field and drop the new column
        # After that re raise the exception
        migrate_name_from_name_to_extra_json(meta, migrate_engine)
        service_table.drop_column('name')
        raise


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    migrate_name_from_name_to_extra_json(meta, migrate_engine)
    service_table = sql.Table('service', meta, autoload=True)
    service_table.drop_column('name')
