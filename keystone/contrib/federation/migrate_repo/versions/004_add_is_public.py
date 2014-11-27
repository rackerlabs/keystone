# Copyright 2014 IBM Corp.
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

import sqlalchemy as sql

_IDP_TABLE_NAME = 'identity_provider'


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    region_table = sql.Table(_IDP_TABLE_NAME, meta, autoload=True)
    column = sql.Column('is_public', sql.Boolean, nullable=True,
                        default=False)
    region_table.create_column(column)


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    region_table = sql.Table(_IDP_TABLE_NAME, meta, autoload=True)
    region_table.drop_column('is_public')
