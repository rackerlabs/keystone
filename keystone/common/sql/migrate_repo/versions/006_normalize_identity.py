# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
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
import string

from sqlalchemy import Column, MetaData, String, Table, types
from sqlalchemy.orm import sessionmaker

disabled_values = ['false', 'disabled', 'no']


def is_enabled(enabled):
    #no explicit value means enabled
    if enabled is None:
        return 1
    if string.lower(enabled) in disabled_values:
        return 0
    return 1


def upgrade_user_table(meta, migrate_engine):
    user_table = Table('user', meta, autoload=True)
    user_table.create_column(Column("password", String(128)))
    user_table.create_column(Column("enabled", types.Boolean))
    maker = sessionmaker(bind=migrate_engine)
    session = maker()
    new_user_data = []
    for a_user in session.query(user_table):
        id, name, extra, password, enabled = a_user
        extra_parsed = json.loads(extra)
        password = extra_parsed['password']
        extra_parsed.pop('password')
        new_user_data.append((password,
                              json.dumps(extra_parsed),
                              is_enabled(enabled), id))
    for new_user in new_user_data:
        session.execute("update user "
                        "set password = '%s', extra = '%s', enabled = '%s' "
                        "where id = '%s'" %
                        new_user)
    session.commit()


def upgrade_tenant_table(meta, migrate_engine):
    user = Table('tenant', meta, autoload=True)
    user.create_column(Column("description", String(128)))
    user.create_column(Column("enabled", types.Boolean))


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine
    upgrade_user_table(meta, migrate_engine)
    upgrade_tenant_table(meta, migrate_engine)


def downgrade(migrate_engine):
    pass
