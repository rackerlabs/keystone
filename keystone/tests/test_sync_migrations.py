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
import itertools
import pkgutil
import re

from oslo.db.sqlalchemy import migration
from oslo.db.sqlalchemy import test_base
from oslo.db.sqlalchemy import test_migrations
import six

import keystone
from keystone.common import sql
from keystone.common.sql import migration_helpers


class RealBackends(type):

    """Meta class produces test cases for all required modules and backends

    Attributes
    ::backends: basic test cases to use real backends for testing.
    ::modules: relative paths to modules containing sqlalchemy models.

    To test all the modules with all the backends necessary to implement a
    number of almost identical test cases. The meta class produces all
    necessary test cases and puts it to a global module namespace. This
    approach helps to keep the module DRY.
    """

    _modules = []
    backends = (test_base.PostgreSQLOpportunisticTestCase,
                test_base.MySQLOpportunisticTestCase)

    @classmethod
    def _append_modules(cls, modules_list):
        """Check for sql modules and append to a list.

        This method works accordingly to an existing in Keystone naming
        convention: all sql models contained in a modules named `sql`.
        """
        for mod in modules_list:
            if mod[1] == 'sql':
                cls._modules.append(
                    '.'.join((mod[0].path.replace('/', '.'), mod[1])))

    @classmethod
    def _separate_packages_modules(cls, modules):
        return (filter(lambda m: m[2], modules),
                filter(lambda m: not m[2], modules))

    @classmethod
    def _get_sql_modules(cls, paths=None):
        """Recursive get all modules and packages.

        :keyword list paths: list of paths of packages for further submodules
                             search
        :returns: list of Python paths of `sql` modules which contain sql
                  models.
        """
        paths = keystone.__path__ if not paths and not cls._modules else paths
        if not paths:
            return cls._modules

        # NOTE(I159): pkgutil.walk_packages takes list of paths but if
        # submodules have a same name only one of them will be in return data.
        all_modules = itertools.chain(
            *[pkgutil.walk_packages([i, ]) for i in paths])
        regexp = re.compile('hacking|tests|common\.*\w*')
        all_modules = filter(lambda p: not regexp.search(p[1]), all_modules)
        packs, modules = cls._separate_packages_modules(all_modules)
        cls._append_modules(modules)
        paths = ['/'.join([p[0].path, p[1]]) for p in packs]
        return cls._get_sql_modules(paths)

    def __new__(cls, name, bases, attrs):
        """Push all created modules to a global modules namespace

        Uses MySQL and Postgresql for testing of all modules containing
        sqlalchemy models. The class itself does not contain any tests.
        """
        for bc in cls.backends:
            bc_name = bc.__name__.replace('OpportunisticTestCase', '')
            nc_bases = bases + (bc, )

            for module in cls._get_sql_modules():
                md_name = module.split('.')[-1].capitalize()
                name = ''.join(('Test', bc_name, md_name))
                nc_attrs = attrs.copy()
                nc_attrs['module'] = '.'.join(('keystone', module))
                globals()[name] = type(name, nc_bases, nc_attrs)
        return type(name, tuple(), {})


class ModelsMigrationsComparer(test_base.DbTestCase):

    """Mixin intended to override test_migrations.ModelsMigrationsSync methods.
    """

    module = None
    models_path = 'backends.sql'
    ignore_list = ['migrate_version']

    def setUp(self):
        super(ModelsMigrationsComparer, self).setUp()
        self.models_module = importlib.import_module(
            '.'.join((self.module, self.models_path)))

    def db_sync(self, engine):
        # NOTE (I159): the migrations are applied for further comparison with
        # the models.
        migration.db_sync(engine=engine,
                          abs_path=migration_helpers.find_migrate_repo(),
                          init_version=sql.migrate_repo.DB_INIT_VERSION)
        abs_path = migration_helpers.find_migrate_repo(
            importlib.import_module(self.module))
        migration.db_version_control(engine, abs_path)
        migration.db_sync(engine, abs_path)

    def include_object(self, object_, name, type_, reflected, compare_to):
        modules = self.models_module.__dict__.values()
        ismodel = lambda m: inspect.isclass(m) and issubclass(m, sql.ModelBase)
        models = [m.__tablename__ for m in modules if ismodel(m)]

        if type_ == 'table':
            return name not in self.ignore_list and name in models
        return True

    def get_engine(self):
        return self.engine

    def get_metadata(self):
        return sql.ModelBase.metadata


@six.add_metaclass(RealBackends)
class TestSyncModelsMigrations(ModelsMigrationsComparer,
                               test_migrations.ModelsMigrationsSync):
    pass
