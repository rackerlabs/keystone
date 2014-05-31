# Copyright (c) 2014 Matthieu Huin <mhu@enovance.com>
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

import sqlalchemy


def upgrade(migrate_engine):
    meta = sqlalchemy.MetaData()
    meta.bind = migrate_engine
    trust_table = sqlalchemy.Table('trust', meta, autoload=True)
    # NOTE(morganfainberg): This upgrade may have occurred at revision 045.
    # Make sure the migration isn't tried again if it has already happened.
    if 'lock' not in trust_table.columns:
        trust_table.create_column(sqlalchemy.Column('lock',
                                  sqlalchemy.String(32),
                                  nullable=True))


def downgrade(migrate_engine):
    # NOTE(morganfainberg): There is no downgrade path since this is handled
    # via a backport for icehouse, downgrade will occur at 045.
    pass
