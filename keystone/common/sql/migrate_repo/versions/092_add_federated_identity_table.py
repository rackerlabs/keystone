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
    meta = sql.MetaData()
    meta.bind = migrate_engine

    identity_table = sql.Table('identity', meta, autoload=True)
    identity_provider_table = sql.Table('identity_provider', meta,
                                        autoload=True)

    federated_table = sql.Table(
        'federated_identity',
        meta,
        sql.Column('id', sql.String(64), primary_key=True,
                   nullable=False),
        sql.Column('identity_id', sql.String(64),
                   sql.ForeignKey(identity_table.c.id, ondelete='CASCADE')),
        sql.Column('idp_id', sql.String(64),
                   sql.ForeignKey(identity_provider_table.c.id,
                                  ondelete='CASCADE')),
        sql.Column('protocol_id', sql.String(64), nullable=False),
        sql.Column('unique_id', sql.String(255), nullable=False),
        sql.Column('display_name', sql.String(255), nullable=True))
    federated_table.create(migrate_engine, checkfirst=True)
