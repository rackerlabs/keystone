#    Licensed under the Apache License, Version 2.0 (the "License"); you may
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

    password_table = sql.Table('password', meta, autoload=True)
    # The created_at_int data cannot really be nullable long term. This
    # corrects the data to be not nullable, but must be done in the contract
    # phase due to "additive only" requirements.
    password_table.c.created_at_int.alter(nullable=False, default=0,
                                          server_default='0')
