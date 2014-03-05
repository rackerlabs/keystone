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
import itertools
import pkgutil

import mock
from sqlalchemy import MetaData

from keystone.common import sql
from keystone.common.sql import migration_helpers
from keystone import exception
from keystone.openstack.common.db.sqlalchemy import migration
from keystone.openstack.common.db.sqlalchemy import test_base
from keystone.openstack.common.db.sqlalchemy import test_migrations


class TestSyncModelsWithMigrations(test_base.DbTestCase,
                                   test_migrations.ModelsMigrationsSync):

    module = None
    models_path = 'backends.sql'
    ignore_list = ['migrate_version', ]
    _models_modules_paths = set()

    def setUp(self):
        super(TestSyncModelsWithMigrations, self).setUp()
        fake_metadata = mock.patch.object(sql.ModelBase, 'metadata',
                                          MetaData(bind=self.get_engine()))
        fake_metadata.start()

        self._models_modules = dict(self._load_models())

        self.addCleanup(fake_metadata.stop)
        self.addCleanup(self._clean_db)

    def _clean_db(self):
        meta = self.get_metadata()
        meta.reflect()
        meta.drop_all()

    def _load_models(self, loaders=None):
        """Sqlalchemy models initializing to a metadata instance

        All the models should be initialized. Therefore all the modules
        which contains sqlalchemy declarative models must be imported before
        the test will be runed. Models loaded in regard of name convention:
        modiles contain models are named `sql.py`.
        """

        loaders = loaders or [pkgutil.get_importer('keystone'), ]
        level_next = list(itertools.chain(
            *[i.iter_modules(prefix=i.path + '/') for i in loaders]))
        self._models_modules_paths |= set(
            map(lambda i: i[0].replace('/', '.'),
                filter(lambda x: x[0].endswith('/sql'), level_next))
        )

        next_loaders = [pkgutil.get_importer(i[0]) for i in level_next if i[1]]
        if next_loaders:
            return self._load_models(next_loaders)
        return dict(((i, importlib.import_module(i))
                    for i in self._models_modules_paths))

    def db_sync(self, engine):
        migration.db_sync(engine, migration_helpers.find_migrate_repo())

        if self.module:
            try:
                abs_path = migration_helpers.find_migrate_repo(
                    importlib.import_module(self.module))
                migration.db_version_control(engine, abs_path)
                migration.db_sync(engine, abs_path)
            except exception.MigrationNotProvided:
                pass
        else:
            self.skip('There is not assigned any module to sync with.')

    def include_object(self, object_, name, type_, reflected, compare_to):
        module_name = '.'.join((self.module, self.models_path))
        module = self._models_modules[module_name]

        def filter_func(attr):
            return isinstance(attr, type) and issubclass(attr, sql.ModelBase)

        tables = map(lambda model: model.__table__.name,
                     filter(filter_func, module.__dict__.itervalues()))
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
