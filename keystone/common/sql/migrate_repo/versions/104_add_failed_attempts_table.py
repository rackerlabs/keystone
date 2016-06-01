# Copyright 2016 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    failed_auth_attempts_table = sql.Table(
        'failed_auth_attempts',
        meta,
        sql.Column('id', sql.Integer, primary_key=True, nullable=False),
        sql.Column('user_id', sql.String(64), nullable=False, index=True),
        sql.Column('timestamp', sql.DateTime())
    )
    failed_auth_attempts_table.create(migrate_engine, checkfirst=True)
