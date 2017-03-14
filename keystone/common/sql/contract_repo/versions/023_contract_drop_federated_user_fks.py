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
from sqlalchemy.engine import reflection


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    inspector = reflection.Inspector.from_engine(migrate_engine)

    federated_table = sql.Table('federated_user', meta, autoload=True)
    idp_table = sql.Table('identity_provider', meta, autoload=True)
    protocol_table = sql.Table('federation_protocol', meta, autoload=True)

    fk_name = _get_fk_name(inspector, 'federated_user', ['idp_id'])
    if fk_name:
        migrate.ForeignKeyConstraint(
            columns=[federated_table.c.idp_id],
            refcolumns=[idp_table.c.id],
            name=fk_name).drop()

    fk_name = _get_fk_name(inspector, 'federated_user',
                           ['protocol_id', 'idp_id'])
    if fk_name:
        migrate.ForeignKeyConstraint(
            columns=[federated_table.c.protocol_id, federated_table.c.idp_id],
            refcolumns=[protocol_table.c.id, protocol_table.c.idp_id],
            name=fk_name).drop()


def _get_fk_name(inspector, table, fk_columns):
    for fk in inspector.get_foreign_keys(table):
        if sorted(fk_columns) == sorted(fk['constrained_columns']):
            return fk['name']
