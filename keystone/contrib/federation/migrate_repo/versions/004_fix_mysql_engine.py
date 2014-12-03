# Copyright 2014 Mirantis.inc
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

import sqlalchemy as sql

from keystone.common.sql import migration_helpers


_TABLE_NAMES = 'identity_provider', 'federation_protocol'
_updated = None


@migration_helpers.only_with_engine('mysql')
def upgrade(migrate_engine):

    meta = sql.MetaData()
    meta.bind = migrate_engine

    global _updated
    _updated = migration_helpers.change_mysql_engine(
        migrate_engine, 'InnoDB', _TABLE_NAMES)

    federation_protocol = sql.Table('federation_protocol', meta, autoload=True)
    fk_col = 'idp_id'
    fk_cols = (i.parent.name for i in federation_protocol.foreign_keys)

    if fk_col not in fk_cols:
        identity_provider = sql.Table('identity_provider', meta, autoload=True)
        constraint = [{'table': federation_protocol,
                       'fk_column': fk_col,
                       'ref_column': identity_provider.c.id}]
        migration_helpers.add_constraints(constraint)


@migration_helpers.only_with_engine('mysql')
def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    if _updated:
        updated = migration_helpers.change_mysql_engine(
            migrate_engine, 'MyISAM', _updated)
        federation_protocol = sql.Table(
            'federation_protocol', meta, autoload=True)

        if 'federation_protocol' in updated:
            fk_col = 'idp_id'
            fk_cols = (i.parent.name for i in federation_protocol.foreign_keys)

            if fk_col not in fk_cols:
                identity_provider = sql.Table(
                    'identity_provider', meta, autoload=True)
                constraint = [{'table': federation_protocol,
                               'fk_column': fk_col,
                               'ref_column': identity_provider.c.id}]
                migration_helpers.add_constraints(constraint)
