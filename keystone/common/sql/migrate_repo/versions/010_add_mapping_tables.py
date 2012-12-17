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

from migrate import *
from sqlalchemy import *

from keystone.common import sql

# these are to make sure all the models we care about are defined
import keystone.catalog.backends.sql
import keystone.contrib.ec2.backends.sql
import keystone.identity.backends.sql
#inentionally leave off token.  We bring it up to V1 here manually


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    meta = MetaData()
    meta.bind = migrate_engine

    sql.ModelBase.metadata.create_all(migrate_engine)

    org_attribute_set = Table(
        'org_attribute_set',
        meta,
        Column('id', sql.String(64), primary_key=True),
        Column('extra', sql.JsonBlob()))

    org_attribute_set.create(migrate_engine, checkfirst=True)

    org_attribute = Table(
        'org_attribute',
        meta,
        Column('id', sql.String(64), primary_key=True),
        Column('type', sql.String(255)),
        Column('value', sql.String(255)),
        Column('extra', sql.JsonBlob()))

    org_attribute.create(migrate_engine, checkfirst=True)

    org_attribute_association = Table(
        'org_attribute_association',
        meta,
        Column('id', sql.String(64), primary_key=True),
        Column(
            'org_attribute_id',
            sql.String(64),
            sql.ForeignKey('org_attribute.id'),
            nullable=False),
        Column(
            'org_attribute_set_id',
            sql.String(64),
            sql.ForeignKey('org_attribute_set.id'),
            nullable=False),
        Column('extra', sql.JsonBlob()))

    org_attribute_association.create(migrate_engine, checkfirst=True)

    # Openstack attributes
    os_attribute_set = Table(
        'os_attribute_set',
        meta,
        Column('id', sql.String(64), primary_key=True),
        Column('extra', sql.JsonBlob()))

    os_attribute_set.create(migrate_engine, checkfirst=True)

    os_attribute_association = Table(
        'os_attribute_association',
        meta,
        Column('id', sql.String(64), primary_key=True),
        Column(
            'attribute_id',
            sql.String(64),
            nullable=False),
        Column(
            'os_attribute_set_id',
            sql.String(64),
            sql.ForeignKey('os_attribute_set.id'),
            nullable=False),
        Column('type', sql.String(255)),
        Column('extra', sql.JsonBlob()))

    os_attribute_association.create(migrate_engine, checkfirst=True)

    # Attribute Mapping
    attribute_mapping = Table(
        'attribute_mapping',
        meta,
        Column('id', sql.String(64), primary_key=True),
        Column(
            'os_attribute_set_id',
            sql.String(64),
            sql.ForeignKey('os_attribute_set.id'),
            nullable=False),
        Column(
            'org_attribute_set_id',
            sql.String(64),
            sql.ForeignKey('org_attribute_set.id'),
            nullable=False),
        Column('extra', sql.JsonBlob()))

    attribute_mapping.create(migrate_engine, checkfirst=True)


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    sql.ModelBase.metadata.drop_all(migrate_engine)

    org_attribute_set = Table(
        'org_attribute_set',
        meta,
        Column('id', sql.String(64), primary_key=True),
        Column('extra', sql.JsonBlob()))

    org_attribute_set.drop(migrate_engine, checkfirst=True)

    org_attribute = Table(
        'org_attribute',
        meta,
        Column('id', sql.String(64), primary_key=True),
        Column('type', sql.String(255)),
        Column('value', sql.String(255)),
        Column('extra', sql.JsonBlob()))

    org_attribute.drop(migrate_engine, checkfirst=True)

    org_attribute_association = Table(
        'org_attribute_association',
        meta,
        Column('id', sql.String(64), primary_key=True),
        Column(
            'org_attribute_id',
            sql.String(64),
            sql.ForeignKey('org_attribute.id'),
            nullable=False),
        Column(
            'org_attribute_set_id',
            sql.String(64),
            sql.ForeignKey('org_attribute_set.id'),
            nullable=False))

    org_attribute_association.drop(migrate_engine, checkfirst=True)

    # Openstack attributes
    os_attribute_set = Table(
        'os_attribute_set',
        meta,
        Column('id', sql.String(64), primary_key=True),
        Column('extra', sql.JsonBlob()))

    os_attribute_set.drop(migrate_engine, checkfirst=True)

    os_attribute_association = Table(
        'os_attribute_association',
        meta,
        Column('id', sql.String(64), primary_key=True),
        Column(
            'attribute_id',
            sql.String(64),
            nullable=False),
        Column(
            'os_attribute_set_id',
            sql.String(64),
            sql.ForeignKey('os_attribute_set.id'),
            nullable=False),
        Column('type', sql.String(255)))

    os_attribute_association.drop(migrate_engine, checkfirst=True)

    # Attribute Mapping
    attribute_mapping = Table(
        'attribute_mapping',
        meta,
        Column('id', sql.String(64), primary_key=True),
        Column(
            'os_attribute_set_id',
            sql.String(64),
            sql.ForeignKey('os_attribute_set.id'),
            nullable=False),
        Column(
            'org_attribute_set_id',
            sql.String(64),
            sql.ForeignKey('org_attribute_set.id'),
            nullable=False))
    attribute_mapping.drop(migrate_engine, checkfirst=True)
