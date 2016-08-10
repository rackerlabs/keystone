# Copyright 2016 OpenStack Foundation
# All Rights Reserved.
#
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

import datetime

import sqlalchemy

from keystone.common import sql
from keystone.common.sql import migration_control


def force_data_migration(release):
    """Migrate any data that is still in old locations.

    This method is called once all the nodes have been upgraded to the new
    release and the operator wants to finish off migrating any data that has
    not already been migrated on-the-fly. Any migration code here must be
    capable of being called repeatedly.

    :param release: name of the release (e.g. 'Newton', 'Ocata' etc.)
    :type release: string

    """
    if release == migration_control.NEWTON_RELEASE:
        _105_add_password_data_columns_tidy_up()


def _105_add_password_data_columns_tidy_up():
    """Migration 105 clean-up.

    In a multi-node migration, this could leave the created_at attribute unset

    """
    with sql.session_for_write() as session:
        meta = sqlalchemy.MetaData()
        meta.bind = session.get_bind()
        password_table = sqlalchemy.Table(
            'password', meta, autoload=True)
        values = {'created_at': datetime.datetime.utcnow()}
        stmt = password_table.update().where(
            password_table.c.created_at is None).values(values)
        stmt.execute()
