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


old_name = None


def upgrade(migrate_engine):
    meta = sa.MetaData(bind=migrate_engine)
    access_token = sa.Table('access_token', meta, autoload=True)

    if migrate_engine.name == 'mysql':
        for i in access_token.indexes:
            if 'consumer_id' in i.name and i.name != 'consumer_id':
                global old_name
                old_name = i.name
                i.rename('consumer_id')
    else:
        sa.Index('consumer_id', access_token.c.consumer_id).create()


def downgrade(migrate_engine):
    meta = sa.MetaData(bind=migrate_engine)
    access_token = sa.Table('access_token', meta, autoload=True)

    if migrate_engine.name == 'mysql':
        for i in access_token.indexes:
            global old_name
            if i.name == 'consumer_id' and old_name:
                i.rename(old_name)
    else:
        sa.Index('consumer_id', access_token.c.consumer_id).drop()
