# Copyright 2014 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


"""Relax the uniqueness of `description` column in region table.

The region table has a dedicated column for the region description. This
column original was not nullable and had to be unique. So if a user wanted to
create a region without sending a description in the request, they would
experience an SQL error because the `description` column can't be null for a
region.

To upgrade, we can still keep the `description` column non-nullable, we will
just relax the uniqueness. If a user does not provide a `description` when
creating a region we check for this case and make sure an empty string is
stored.

For downgrade, we are just going to set unique=True on the `description`
column.
"""

import sqlalchemy as sql
from sqlalchemy.orm import sessionmaker


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    session = sessionmaker(bind=migrate_engine)()

    session.execute('ALTER TABLE region DROP INDEX description;')

def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    session = sessionmaker(bind=migrate_engine)()

    session.execute('CREATE UNIQUE INDEX description ON region '
                    '(description);')
