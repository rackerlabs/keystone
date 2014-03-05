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
import inspect

from keystone.common import sql
from keystone.common.sql import migration_helpers
from keystone import exception
from keystone.openstack.common.db.sqlalchemy import migration
from keystone.openstack.common.db.sqlalchemy import test_base
from keystone.openstack.common.db.sqlalchemy import test_migrations


class SyncModelsWithMigrations(test_base.DbTestCase,
                               test_migrations.ModelsMigrationsSync):

    module = None
    models_path = 'backends.sql'
    ignore_list = ['migrate_version', ]

    def setUp(self):
        super(SyncModelsWithMigrations, self).setUp()
        if not self.module:
            self.skip('There is not assigned any module to sync with.')

        self.models_module = importlib.import_module(
            '.'.join((self.module, self.models_path)))

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
        models = [m.__tablename__
                  for m in self.models_module.__dict__.itervalues()
                  if inspect.isclass(m) and issubclass(m, sql.ModelBase)]

        if type_ == 'table':
            return name not in self.ignore_list and name in models
        elif type_ == 'column':
            return True

    def get_engine(self):
        return self.engine

    def get_metadata(self):
        return sql.ModelBase.metadata


class TestSyncTrust(SyncModelsWithMigrations):

    module = 'keystone.trust'


class TestSyncIdentity(SyncModelsWithMigrations):

    module = 'keystone.identity'


class TestSyncOauth1(SyncModelsWithMigrations):

    module = 'keystone.contrib.oauth1'


class TestSyncFederation(SyncModelsWithMigrations):

    module = 'keystone.contrib.federation'


class TestSyncEndpointFilter(SyncModelsWithMigrations):

    module = 'keystone.contrib.endpoint_filter'


class TestSyncToken(SyncModelsWithMigrations):

    module = 'keystone.token'


class TestSyncAssignment(SyncModelsWithMigrations):

    module = 'keystone.assignment'


class TestSyncCredential(SyncModelsWithMigrations):

    module = 'keystone.credential'


class TestSyncPolicy(SyncModelsWithMigrations):

    module = 'keystone.policy'


class TestSyncCatalog(SyncModelsWithMigrations):

    module = 'keystone.catalog'
