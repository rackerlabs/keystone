# Copyright 2014 Mirantis.inc
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import importlib

from keystone.common import sql
from keystone.common.sql import migration_helpers
from keystone import exception
from keystone.openstack.common.db.sqlalchemy import migration
from keystone.openstack.common.db.sqlalchemy import test_base
from keystone.openstack.common.db.sqlalchemy import test_migrations


class TestSyncModelsWithMigrations(test_base.DbTestCase,
                                   test_migrations.ModelsMigrationsSync):

    models_path = 'backends.sql'
    ignore_list = ['migrate_version', ]

    def setUp(self):
        super(TestSyncModelsWithMigrations, self).setUp()
        self.models_module = importlib.import_module(
            '.'.join((self.module, self.models_path)))

    @property
    def module(self):
        self.skip('There is not assigned any module to sync with.')

    def db_sync(self, engine):
        migration.db_sync(engine, migration_helpers.find_migrate_repo())
        try:
            abs_path = migration_helpers.find_migrate_repo(
                importlib.import_module(self.module))
            migration.db_version_control(engine, abs_path)
            migration.db_sync(engine, abs_path)
        except exception.MigrationNotProvided:
            pass

    def include_object(self, object_, name, type_, reflected, compare_to):
        def filter_func(attr):
            return isinstance(attr, type) and issubclass(attr, sql.ModelBase)

        tables = map(lambda model: model.__table__.name, filter(
            filter_func, self.models_module.__dict__.itervalues()))
        return name not in self.ignore_list and name in tables

    def get_engine(self):
        return self.engine

    def get_metadata(self):
        return sql.ModelBase.metadata


class TestSyncTrust(TestSyncModelsWithMigrations):

    module = 'keystone.trust'


class TestSyncIdentity(TestSyncModelsWithMigrations):

    module = 'keystone.identity'


class TestSyncOauth1(TestSyncModelsWithMigrations):

    module = 'keystone.contrib.oauth1'


class TestSyncFederation(TestSyncModelsWithMigrations):

    module = 'keystone.contrib.federation'


class TestSyncEndpointFilter(TestSyncModelsWithMigrations):

    module = 'keystone.contrib.endpoint_filter'


class TestSyncToken(TestSyncModelsWithMigrations):

    module = 'keystone.token'


class TestSyncAssignment(TestSyncModelsWithMigrations):

    module = 'keystone.assignment'


class TestSyncCredential(TestSyncModelsWithMigrations):

    module = 'keystone.credential'


class TestSyncPolicy(TestSyncModelsWithMigrations):

    module = 'keystone.policy'


class TestSyncCatalog(TestSyncModelsWithMigrations):

    module = 'keystone.catalog'
