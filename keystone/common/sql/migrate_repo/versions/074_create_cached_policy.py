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

import sqlalchemy

from keystone.common import sql


POLICY_CACHE_TABLE = 'policy_cache'


def upgrade(migrate_engine):
    meta = sqlalchemy.MetaData()
    meta.bind = migrate_engine

    policy_cache_table = sqlalchemy.Table(
        POLICY_CACHE_TABLE,
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('blob', sql.JsonBlob(), nullable=False),
        sql.Column('type', sql.String(255), nullable=False),
        sql.Column('extra', sql.JsonBlob()),
        sql.Column('valid_to', sql.DateTime, nullable=False),
        mysql_engine='InnoDB',
        mysql_charset='utf8')

    policy_cache_table.create(migrate_engine, checkfirst=True)
