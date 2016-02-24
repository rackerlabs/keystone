# Copyright 2016 eBay Inc.
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

import migrate
import sqlalchemy as sql


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    token_table = sql.Table('token', meta, autoload=True)

    to_drop = None
    if migrate_engine.name == 'mysql':
        for index in token_table.indexes:
            if (index.unique and len(index.columns) == 2 and
                    'expires' in index.columns and 'valid' in index.columns):
                to_drop = index
                break
    else:
        for index in token_table.constraints:
            if (len(index.columns) == 2 and 'expires' in index.columns and
                    'valid' in index.columns):
                to_drop = index
                break

    # remove the original index
    if migrate_engine.name != 'sqlite' and to_drop is not None:
        migrate.UniqueConstraint(token_table.c.expires,
                                 token_table.c.valid,
                                 name=to_drop.name).drop()

    # create new index in the right order
    sql.Index('ix_token_valid_expires', token_table.c.valid,
              token_table.c.expires).create()
