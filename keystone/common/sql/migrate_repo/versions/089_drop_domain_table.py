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

_DOMAIN_TABLE_NAME = 'domain'


def upgrade(migrate_engine):

    meta = sql.MetaData()
    meta.bind = migrate_engine

    domain_table = sql.Table(_DOMAIN_TABLE_NAME, meta, autoload=True)

    if migrate_engine.name != 'sqlite':
        domain_table.drop(migrate_engine, checkfirst=True)
