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

    _module = None
    _models_path = 'backends.sql'
    _ignore_list = ['migrate_version', ]

    def setUp(self):
        super(TestSyncModelsWithMigrations, self).setUp()
        self.addCleanup(self._clear_metadata)

    def _clear_metadata(self):
        meta = self.get_metadata()
        meta.reflect()
        meta.drop_all()
        meta.clear()

    def db_sync(self, engine):
        migration.db_sync(engine, migration_helpers.find_migrate_repo())

        if self._module:
            importlib.import_module(
                '.'.join((self._module, self._models_path)))

            try:
                abs_path = migration_helpers.find_migrate_repo(
                    importlib.import_module(self._module))
                migration.db_version_control(engine, abs_path)
                migration.db_sync(engine, abs_path)
            except exception.MigrationNotProvided:
                pass
        else:
            self.skip('There is not assigned any module to sync with.')

    def include_object(self, object_, name, type_, reflected, compare_to):
        meta_tables = self.get_metadata().tables
        return name not in self._ignore_list and name in meta_tables

    def get_engine(self):
        return self.engine

    def get_metadata(self):
        sql.ModelBase.metadata.bind = self.get_engine()
        return sql.ModelBase.metadata


class TestSyncTrust(TestSyncModelsWithMigrations):

    _module = 'keystone.trust'


class TestSyncIdentity(TestSyncModelsWithMigrations):

    _module = 'keystone.identity'


class TestSyncOauth1(TestSyncModelsWithMigrations):

    _module = 'keystone.contrib.oauth1'


class TestSyncFederation(TestSyncModelsWithMigrations):

    _module = 'keystone.contrib.federation'


class TestSyncEndpointFilter(TestSyncModelsWithMigrations):

    _module = 'keystone.contrib.endpoint_filter'


class TestSyncToken(TestSyncModelsWithMigrations):

    _module = 'keystone.token'


class TestSyncAssignment(TestSyncModelsWithMigrations):

    _module = 'keystone.assignment'


class TestSyncCredential(TestSyncModelsWithMigrations):

    _module = 'keystone.credential'


class TestSyncPolicy(TestSyncModelsWithMigrations):

    _module = 'keystone.policy'


class TestSyncCatalog(TestSyncModelsWithMigrations):

    _module = 'keystone.catalog'
