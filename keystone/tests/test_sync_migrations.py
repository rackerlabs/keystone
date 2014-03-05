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

from keystone.common import sql
from keystone.common.sql import migration_helpers
from keystone import exception
from keystone.openstack.common.db.sqlalchemy import migration
from keystone.openstack.common.db.sqlalchemy import test_base
from keystone.openstack.common.db.sqlalchemy import test_migrations


class TestSyncModelsWithMigrations(test_base.DbTestCase,
                                   test_migrations.ModelsMigrationsSync):

    sql_modules_paths = set()
    sql_modules = []

    def __init__(self, *args, **kwargs):
        super(TestSyncModelsWithMigrations, self).__init__(*args, **kwargs)
        self._loader()

    def _loader(self, loaders=None):
        """All the models should be initialized. Therefore all the modules
        which contains sqlalchemy models must be imported before the test will
        be runed.
        """

        loaders = loaders or [pkgutil.get_importer('keystone'), ]
        level_next = list(itertools.chain(
            *[i.iter_modules(prefix=i.path + '/') for i in loaders]))
        self.sql_modules_paths |= set(
            map(lambda i: i[0].replace('/', '.'),
                filter(lambda x: x[0].endswith('/sql'), level_next))
        )
        next_loaders = [pkgutil.get_importer(i[0]) for i in level_next if i[1]]
        if next_loaders:
            return self._loader(next_loaders)
        for i in self.sql_modules_paths:
            self.sql_modules.append(importlib.import_module(i))

    def db_sync(self, engine):
        """All migrations syunchronyzation."""
        for i in self.sql_modules_paths:
            try:
                abs_path = migration_helpers.find_migrate_repo(
                    importlib.import_module(i.replace('.backends.sql', ''))
                )
            except exception.MigrationNotProvided:
                continue

            migration.db_version_control(engine, abs_path)
            migration.db_sync(engine, abs_path)

    def include_object(slef, object_, name, type_, reflected, compare_to):
        return name not in ['migrate_version', ]

    def get_engine(self):
        return self.engine

    def get_metadata(self):
        return sql.ModelBase.metadata
