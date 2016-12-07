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
from sqlalchemy.orm import sessionmaker
import sqlalchemy.sql.expression as expression


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    maker = sessionmaker(bind=migrate_engine)
    session = maker()

    user_table = sql.Table('user', meta, autoload=True)
    federated_table = sql.Table('federated_user', meta, autoload=True)
    idp_table = sql.Table('identity_provider', meta, autoload=True)

    federated_users = list(federated_table.select().execute())
    for federated_user in federated_users:
        values = _get_domain_value(session, federated_user.idp_id, idp_table)
        stmt = user_table.update().where(
            sql.and_(
                user_table.c.domain_id == expression.null(),
                user_table.c.id == federated_user.user_id)).values(values)
        stmt.execute()


def _get_domain_value(session, idp_id, idp_table):
    cols = [idp_table.c.domain_id]
    where_filter = idp_table.c.id == idp_id
    statement = sql.select(cols).where(where_filter)
    domain = session.execute(statement).fetchone()
    return {'domain_id': domain[0]}
