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

from keystone.federation.backends import sql as sql_backend


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    maker = sessionmaker(bind=migrate_engine)
    session = maker()

    identity_providers = sql.Table('identity_provider', meta, autoload=True)
    protocols = sql.Table('federation_protocol', meta, autoload=True)
    for idp in identity_providers.select().execute():
        group_id = _find_group_id_from_mapping(idp['id'], protocols, session)
        print(group_id)
        if group_id:
            domain_id = _get_group_domain(group_id)
        if not domain_id:
            domain_id = _create_idp_domain(idp['id'])
        _update_idp_domain(idp['id'], domain_id)


def _find_group_id_from_mapping(idp_id, protocols, session):
    for p in protocols.select().where(protocols.c.idp_id == idp_id).execute():
        federation = sql_backend.Federation()
        mapping = federation._get_mapping(session, p['mapping_id']).to_dict()
        for rule in mapping['rules']:
            for local in rule['local']:
                for k, v in local.items():
                    if k == 'group':
                        return v.get('id')
    return None


def _get_group_domain(group_id):
    pass


def _create_idp_domain(idp_id):
    pass


def _update_idp_domain(idp_id, domain_id):
    pass
