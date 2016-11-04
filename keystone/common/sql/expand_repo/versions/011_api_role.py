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
    sql.Table('role', meta, autoload=True)
    
    api = sql.Table(
        'api', meta,
        sql.Column('id', sql.String(length=64), primary_key=True),
        sql.Column('service', sql.String(length=64), nullable=True),
        sql.Column('verb', sql.String(length=64), nullable=True),
        sql.Column('pattern', sql.Text, nullable=True),
        mysql_engine='InnoDB',
        mysql_charset='utf8')
    api.create()

    api_role = sql.Table(
        'api_role', meta,
        sql.Column('api_id', sql.String(length=64),
                   sql.ForeignKey('api.id'),
                   primary_key=True),
        sql.Column('role_id', sql.String(length=64),
                   sql.ForeignKey('role.id'),
                   nullable=False, default=False,
                   primary_key=True),
        mysql_engine='InnoDB',
        mysql_charset='utf8')
    api_role.create()
