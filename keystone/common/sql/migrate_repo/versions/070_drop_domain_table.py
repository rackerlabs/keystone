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

from keystone.common import sql as ks_sql

_PROJECT_TABLE_NAME = 'project'
_DOMAIN_TABLE_NAME = 'domain'


def upgrade(migrate_engine):

    meta = sql.MetaData()
    meta.bind = migrate_engine

    domain_table = sql.Table(_DOMAIN_TABLE_NAME, meta, autoload=True)
    domain_table.drop(migrate_engine, checkfirst=True)


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine
    session = sql.orm.sessionmaker(bind=migrate_engine)()
    domain = sql.Table(
        _DOMAIN_TABLE_NAME, meta,
        sql.Column('id', sql.String(length=64), primary_key=True),
        sql.Column('name', sql.String(length=64), nullable=False),
        sql.Column('enabled', sql.Boolean, default=True, nullable=False),
        sql.Column('extra', ks_sql.JsonBlob.impl))

    domain.create(migrate_engine, checkfirst=True)
    project_table = sql.Table(_PROJECT_TABLE_NAME, meta, autoload=True)
    domain_table = sql.Table(_DOMAIN_TABLE_NAME, meta, autoload=True)

    projects = list(project_table.select().execute())
    for project in projects:
        if project.is_domain:
            domain = {'name': project.name,
                      'id': project.id,
                      'enabled': project.enabled}
            insert = domain_table.insert().values(**domain)
            session.execute(insert)
            session.commit()

    session.close()
