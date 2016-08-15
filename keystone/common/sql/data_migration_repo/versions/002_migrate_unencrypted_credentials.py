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

from keystone.common import dependency


@dependency.requires('credential_provider_api')
class CredentialEncryptor(object):

    def encrypt(self, unencrypted_blob):
        # NOTE(lbragstad): Since this data migration has a hard dependency on a
        # provider, we want to make sure that all dependencies have been
        # resolved before using it. If we don't do this it is possible to get
        # AttributeErrors during a migration because the
        # self.credential_provider_api dependency hasn't been resolved yet.
        dependency.resolve_future_dependencies()
        encrypted_blob = self.credential_provider_api.encrypt(unencrypted_blob)
        primary_key_hash = self.credential_provider_api.primary_key_hash
        return (encrypted_blob, primary_key_hash)


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    session = sql.orm.sessionmaker(bind=migrate_engine)()

    credential_table = sql.Table('credential', meta, autoload=True)
    credentials = list(credential_table.select().execute())

    credential_encryptor = CredentialEncryptor()
    for credential in credentials:
        encrypted_blob, primary_key_hash = credential_encryptor.encrypt(
            credential['blob']
        )
        values = {
            'encrypted_blob': encrypted_blob,
            'key_hash': primary_key_hash
        }
        update = credential_table.update().where(
            credential_table.c.id == credential.id
        ).values(values)
        session.execute(update)
        session.commit()
    session.close()
