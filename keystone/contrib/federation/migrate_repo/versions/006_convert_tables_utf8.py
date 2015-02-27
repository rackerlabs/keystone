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

    idp_table_temp = sql.Table(
        'identity_provider',
        meta,
        autoload=True)
    idp_table_temp.rename("identity_provider_temp")
    federation_protocol_table_temp = sql.Table(
        'federation_protocol',
        meta,
        autoload=True)
    federation_protocol_table_temp.rename("federation_protocol_temp")
    mapping_table_temp = sql.Table(
        'mapping',
        meta,
        autoload=True)
    mapping_table_temp.rename("mapping_temp")
    meta.clear()

    idp_table_temp = sql.Table(
        'identity_provider_temp',
        meta,
        autoload=True)
    idp_table_temp.rename("identity_provider_temp")
    federation_protocol_table_temp = sql.Table(
        'federation_protocol_temp',
        meta,
        autoload=True)
    federation_protocol_table_temp.rename("federation_protocol_temp")
    mapping_table_temp = sql.Table(
        'mapping_temp',
        meta,
        autoload=True)
    mapping_table_temp.rename("mapping_temp")
    idp_table = sql.Table(
        'identity_provider',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('enabled', sql.Boolean, nullable=False),
        sql.Column('description', sql.Text(), nullable=True),
        mysql_engine='InnoDB',
        mysql_charset='utf8')
    idp_table.create(migrate_engine, checkfirst=True)
    federation_protocol_table = sql.Table(
        'federation_protocol',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('idp_id', sql.String(64),
                   sql.ForeignKey('identity_provider.id', ondelete='CASCADE'),
                   primary_key=True),
        sql.Column('mapping_id', sql.String(64), nullable=True),
        mysql_engine='InnoDB',
        mysql_charset='utf8')
    federation_protocol_table.create(migrate_engine, checkfirst=True)
    mapping_table = sql.Table(
        'mapping',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('rules', sql.Text(), nullable=False),
        mysql_engine='InnoDB',
        mysql_charset='utf8')
    mapping_table.create(migrate_engine, checkfirst=True)

    idps_list = migrate_engine.execute(sql.select([idp_table_temp]))
    for idp in idps_list:
        migrate_engine.execute(idp_table.insert(idp))

    mappings_list = migrate_engine.execute(sql.select([mapping_table_temp]))
    for map in mappings_list:
        migrate_engine.execute(mapping_table.insert(map))

    fed_proto_list = migrate_engine.execute(
        sql.select([federation_protocol_table_temp]))
    for protocol in fed_proto_list:
        migrate_engine.execute(federation_protocol_table.insert(protocol))

    federation_protocol_table_temp.drop(migrate_engine, checkfirst=True)
    idp_table_temp.drop(migrate_engine, checkfirst=True)
    mapping_table_temp.drop(migrate_engine, checkfirst=True)


def downgrade(migrate_engine):
    pass
