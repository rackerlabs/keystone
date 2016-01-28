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

    SERVICE_PROVIDER_GROUP_ID = 'service_provider_group_id'
    SERVICE_PROVIDER_ID = 'service_provider_id'

    endpoint_group_table = sql.Table(
        'service_providers_group',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(255), nullable=False),
        sql.Column('description', sql.Text, nullable=True))
    endpoint_group_table.create(migrate_engine, checkfirst=True)

    # FIXME(marek-denis): Add a ForeignKey contraint for 'service_provider'
    # entity
    project_endpoint_group_table = sql.Table(
        'service_providers_group_members',
        meta,
        sql.Column(SERVICE_PROVIDER_GROUP_ID, sql.String(64),
                   sql.ForeignKey('service_providers_group.id'),
                   nullable=False),
        sql.Column(SERVICE_PROVIDER_ID, sql.String(64),
                   nullable=False),
        sql.PrimaryKeyConstraint(SERVICE_PROVIDER_GROUP_ID,
                                 SERVICE_PROVIDER_ID))
    project_endpoint_group_table.create(migrate_engine, checkfirst=True)
