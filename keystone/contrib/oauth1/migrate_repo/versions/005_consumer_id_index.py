# Copyright 2014 Mirantis.inc
# All Rights Reserved.
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

import sqlalchemy as sa


def upgrade(migrate_engine):
    meta = sa.MetaData(bind=migrate_engine)
    table = sa.Table('access_token', meta, autoload=True)

    if migrate_engine.name == 'mysql':
        index = 'consumer_id'
        # NOTE(i159): several problems solved here:
        # * MySQL requires indexes on foreign keys. Such an index is created on
        # the referencing table automatically if it does not exist.
        # * MySQL 5.5. renames fk indexes, MySQL 5.1 leaves an indexes without
        # changes.
        # * Alembic can exclude from comparision only index with the name equal
        # to a column name.
        # * We need to explicitly revert an index name if it was renamed,
        # to have version independent behavior.
        # * MySQL can't rename index, it can just delete it and create another
        # one, with different name.
        # * Substitute an index with the same name is impossible
        # too, it causes an error.
        # So we must ensure that correct index was renamed and revert it.
        if [i for i in table.indexes if i.name != index and index in i.name]:
            sa.Index(index, table.c.consumer_id).create()


def downgrade(migrate_engine):
    pass
