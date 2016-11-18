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
import uuid

from keystone.resource.backends import base


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    maker = sessionmaker(bind=migrate_engine)
    session = maker()

    idp_table = sql.Table('identity_provider', meta, autoload=True)
    idp_count = sql.select([sql.func.count()]).select_from(
        idp_table).execute().fetchone()[0]

    if idp_count > 0:
        # create new federated domain
        federated_domain = {
            'id': uuid.uuid4().hex,
            'name': 'Federated',
            'enabled': True,
            'description': 'The default domain for federated users.',
            'domain_id': base.NULL_DOMAIN_ID,
            'is_domain': True,
            'parent_id': None,
            'extra': '{}'
        }
        project_table = sql.Table('project', meta, autoload=True)
        new_row = project_table.insert().values(**federated_domain)
        session.execute(new_row)
        session.commit()

        # update idps with the federated domsin_id
        values = {'domain_id': federated_domain['id']}
        stmt = idp_table.update().where(
            idp_table.c.domain_id == expression.null()).values(values)
        stmt.execute()

    # set not nullable
    idp_table.c.domain_id.alter(nullable=False)
