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


def upgrade(migrate_engine):
    # Add the domain_scope_id column to the revocation_event table.
    meta = sql.MetaData()
    meta.bind = migrate_engine

    revocation_event_table = sql.Table('revocation_event', meta, autoload=True)
    domain_scope_id_column = sql.Column('domain_scope_id', sql.String(64))
    domain_scope_id_column.create(revocation_event_table)


def downgrade(migrate_engine):
    # Drop the domain_scope_id column from the revocation_event table.
    meta = sql.MetaData()
    meta.bind = migrate_engine

    revocation_event_table = sql.Table('revocation_event', meta, autoload=True)
    revocation_event_table.c.domain_scope_id.drop()
