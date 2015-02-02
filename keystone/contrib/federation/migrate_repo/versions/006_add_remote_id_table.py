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


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    idp_table = sql.Table('identity_provider', meta, autoload=True)
    # NOTE: the table should be utf8 but this create problems with
    # identity_provider table which is not. Both should be fixed
    remote_id_table = sql.Table(
        'idp_remote_ids',
        meta,
        sql.Column('idp_id',
                   sql.String(64),
                   sql.ForeignKey('identity_provider.id',
                                  ondelete='CASCADE'),
                   primary_key=True),
        sql.Column('remote_id',
                   sql.String(255),
                   primary_key=True,
                   unique=True))

    remote_id_table.create(migrate_engine, checkfirst=True)
    migrate_engine.execute('INSERT INTO idp_remote_ids (idp_id,remote_id) '
                           'SELECT id, remote_id FROM identity_provider')
    idp_table.drop_column('remote_id')


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    idp_table = sql.Table('identity_provider', meta, autoload=True)
    remote_id = sql.Column('remote_id', sql.String(256), nullable=True)
    idp_table.create_column(remote_id)
    # NOTE: version 004 does not support multiple remote_ids so only the
    #       first is restored and the other dropped
    migrate_engine.execute('UPDATE identity_provider SET remote_id=(SELECT '
                           'remote_id from idp_remote_ids WHERE '
                           'idp_remote_ids.idp_id=identity_provider.id)')
    table = sql.Table('idp_remote_ids', meta, autoload=True)
    table.drop()
