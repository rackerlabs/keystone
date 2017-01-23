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

import keystone.conf


CONF = keystone.conf.CONF


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    ignore_password_expiry_user_ids = \
        CONF.security_compliance.password_expires_ignore_user_ids
    user_table = sql.Table('user', meta, autoload=True)

    values = {'ignore_password_expiry': True}
    for uid in ignore_password_expiry_user_ids:
        stmt = user_table.update().where(user_table.c.id == uid).values(values)
        stmt.execute()
