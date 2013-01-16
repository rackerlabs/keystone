# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
#
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
# TODO(henry-nash): Remove next two items, since only required for
# temp default domain
import json
from sqlalchemy import orm


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    meta = sql.MetaData()
    meta.bind = migrate_engine

    domain_table = sql.Table(
        'domain',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('name', sql.String(64), unique=True, nullable=False),
        sql.Column('enabled', sql.Boolean, default=True),
        sql.Column('extra', sql.Text()))
    domain_table.create(migrate_engine, checkfirst=True)

    # TODO(henry-nash): Remove the addition of the default domain once Dolphm's
    # change is in.
    
    domain = {
        'id': 'default',
        'name': 'Default',
        'enabled': True,
        'extra': json.dumps({
            'description': 'Owns users and tenants (i.e. projects) available '
                           'on Identity API v2.'})}
    
    session = orm.sessionmaker(bind=migrate_engine)()
    
    session.execute(
        'INSERT INTO `%s` (%s) VALUES (%s)' % (
            domain_table.name,
                ', '.join(['`%s`' % k for k in domain.keys()]),
                ', '.join([':%s' % k for k in domain.keys()])),
            domain)
    session.commit()

    user = sql.Table('user', meta, autoload=True)
    user_domain_metadata_table = sql.Table(
        'user_domain_metadata',
        meta,
        sql.Column(
            'user_id',
            sql.String(64),
            sql.ForeignKey('user.id'),
            primary_key=True),
        sql.Column(
            'domain_id',
            sql.String(64),
            sql.ForeignKey('domain.id'),
            primary_key=True),
        sql.Column('data', sql.Text()))
    user_domain_metadata_table.create(migrate_engine, checkfirst=True)

    sql.Table('tenant', meta, autoload=True)
    credential_table = sql.Table(
        'credential',
        meta,
        sql.Column('id', sql.String(64), primary_key=True),
        sql.Column('user_id',
                   sql.String(64),
                   sql.ForeignKey('user.id'),
                   nullable=False),
        sql.Column('project_id',
                   sql.String(64),
                   sql.ForeignKey('tenant.id')),
        sql.Column('blob', sql.Text(), nullable=False),
        sql.Column('type', sql.String(255), nullable=False),
        sql.Column('extra', sql.Text()))
    credential_table.create(migrate_engine, checkfirst=True)

    role = sql.Table('role', meta, autoload=True)
    extra = sql.Column('extra', sql.Text())
    role.create_column(extra)


def downgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    role = sql.Table('role', meta, autoload=True)
    role.drop_column('extra')

    user = sql.Table('user', meta, autoload=True)
    user.drop_column('domain_id')

    tables = ['user_domain_metadata', 'credential', 'domain']
    for t in tables:
        table = sql.Table(t, meta, autoload=True)
        table.drop(migrate_engine, checkfirst=True)
