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

import migrate
import sqlalchemy as sql


def upgrade(migrate_engine):
    ENDPOINT_TABLE_NAME = 'endpoint'
    SERVICE_TABLE_NAME = 'service'

    metadata = sql.MetaData()
    metadata.bind = migrate_engine

    # Retrieve the existing service table
    service_table = sql.Table(SERVICE_TABLE_NAME, metadata, autoload=True)
    # Retrieve the existing endpoint table
    endpoint_table = sql.Table(ENDPOINT_TABLE_NAME, metadata, autoload=True)

    # drop FK constraint
    migrate.ForeignKeyConstraint(columns=[endpoint_table.c.service_id],
                                 refcolumns=[service_table.c.id]).drop()

    # create FK constraint with 'ondelete' keyword argument
    migrate.ForeignKeyConstraint(columns=[endpoint_table.c.service_id],
                                 refcolumns=[service_table.c.id],
                                 ondelete='CASCADE').create()
