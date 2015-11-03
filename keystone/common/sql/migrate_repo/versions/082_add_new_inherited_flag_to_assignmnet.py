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
from sqlalchemy.sql.expression import false


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    assignment_table = sql.Table('assignment', meta, autoload=True)
    core_inherited_column = sql.Column(
        'inherited_core', sql.Boolean, default=False, server_default=false(),
        nullable=False)
    assignment_table.create_column(core_inherited_column)
