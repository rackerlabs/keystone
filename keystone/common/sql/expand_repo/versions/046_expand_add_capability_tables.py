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

    application_credential_table = sql.Table('application_credential', meta,
                                             None, autoload=True)

    url_path_template = sql.Table(
        'url_path_template', meta,
        sql.Column('internal_id', sql.Integer, primary_key=True,
                   nullable=False),
        sql.Column('id', sql.String(length=64),
                   nullable=False),
        sql.Column('template_string', sql.Text(), nullable=False),
        sql.Column('allow_chained', sql.Boolean(), nullable=False,
                   server_default='0'),
        sql.UniqueConstraint('id', name='duplicate_id_constraint'),
        mysql_engine='InnoDB',
        mysql_charset='utf8')

    capability = sql.Table(
        'capability', meta,
        sql.Column('internal_id', sql.Integer, primary_key=True,
                   nullable=False),
        sql.Column('application_credential_id', sql.Integer,
                   sql.ForeignKey(application_credential_table.c.internal_id,
                                  ondelete='CASCADE'),
                   index=True, nullable=False),
        sql.Column('id', sql.String(length=64),
                   nullable=False),
        sql.Column('url_path', sql.Text(),
                   nullable=False),
        sql.Column('service_uuid', sql.String(length=64), nullable=False),
        sql.Column('allow_chained', sql.Boolean(), nullable=False,
                   server_default='0'),
        sql.Column('request_type', sql.String(length=7),
                   nullable=False),
        mysql_engine='InnoDB',
        mysql_charset='utf8')

    url_path_template_key = sql.Table(
        'url_path_template_key', meta,
        sql.Column('internal_id', sql.Integer, primary_key=True,
                   nullable=False),
        sql.Column('url_path_template_id', sql.Integer,
                   sql.ForeignKey(url_path_template.c.internal_id,
                                  ondelete='CASCADE'),
                   index=True, nullable=False),
        sql.Column('key', sql.String(255),
                   nullable=False),
        sql.Column('type', sql.Enum('context', 'user'), nullable=False),
        mysql_engine='InnoDB',
        mysql_charset='utf8')

    url_path_template_value = sql.Table(
        'url_path_template_value', meta,
        sql.Column('internal_id', sql.Integer, primary_key=True,
                   nullable=False),
        sql.Column('capability_id', sql.Integer,
                   sql.ForeignKey(capability.c.internal_id,
                                  ondelete='CASCADE'),
                   index=True, nullable=False),
        sql.Column('key', sql.String(255),
                   nullable=False),
        sql.Column('value', sql.String(255),
                   nullable=True),
        mysql_engine='InnoDB',
        mysql_charset='utf8')

    url_path_template.create(migrate_engine, checkfirst=True)
    capability.create(migrate_engine, checkfirst=True)
    url_path_template_key.create(migrate_engine, checkfirst=True)
    url_path_template_value.create(migrate_engine, checkfirst=True)
