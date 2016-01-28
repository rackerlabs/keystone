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
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    meta = sql.MetaData()
    meta.bind = migrate_engine
    # NOTE(marek-denis): Load 'service_provider' table as it's later required
    # for adding ForeignKey in the service_providers_group_id table
    sql.Table('service_provider', meta, autoload=True)
    service_providers_group_table = sql.Table(
        'service_providers_group',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(255), nullable=False),
        sql.Column('description', sql.Text, nullable=True))
    service_providers_group_table.create(migrate_engine, checkfirst=True)

    service_providers_group_members_table = sql.Table(
        'service_providers_group_members',
        meta,
        sql.Column('service_providers_group_id', sql.String(64),
                   sql.ForeignKey('service_providers_group.id',
                                  ondelete='CASCADE'), nullable=False),
        sql.Column('service_provider_id', sql.String(64),
                   sql.ForeignKey('service_provider.id', ondelete='CASCADE'),
                   nullable=False),
        sql.PrimaryKeyConstraint('service_providers_group_id',
                                 'service_provider_id'))
    service_providers_group_members_table.create(migrate_engine,
                                                 checkfirst=True)
