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

from oslo.db.sqlalchemy import migration
from oslo.db.sqlalchemy import test_base
from oslo.db.sqlalchemy import test_migrations
import six

from keystone.common import sql
from keystone.common.sql import migration_helpers
from keystone import exception


class RealBackends(object):

    """Meta class produces test cases for all required modules and backends

    Attributes
    ::backends: basic test cases to use real backends for testing.
    ::modules: relative paths to modules containing sqlalchemy models.

    To test all the modules with all the backends necessary to implement a
    number of almost identical test cases. The meta class produces all
    necessary test cases and puts it to a global module namespace. This
    approach helps to keep the module DRY.
    """

    backends = (test_base.PostgreSQLOpportunisticTestCase,
                test_base.MySQLOpportunisticTestCase)
    modules = (
        'trust',
        'identity',
        'contrib.oauth1',
        'contrib.federation',
        'contrib.endpoint_filter',
        'token',
        'assignment',
        'credential',
        'policy',
        'catalog')

    def __new__(cls, name, bases, attrs):
        """Push all created modules to a global modules namespace

        Uses all real backends for all modules containing sqlalchemy models.
        The class itself does not contain any tests.
        """
        for bc in cls.backends:
            bc_name = bc.__name__.replace('OpportunisticTestCase', '')
            nc_bases = bases + (bc, )

            for module in cls.modules:
                md_name = module.split('.')[-1].capitalize()
                name = ''.join(('Test', bc_name, md_name))
                nc_attrs = attrs.copy()
                nc_attrs['module'] = '.'.join(('keystone', module))
                globals()[name] = type(name, nc_bases, nc_attrs)
        return type(name, tuple(), {})


class ModelsMigrationsComparer(test_base.DbTestCase):

    """Mixin intended to override ModelsMigrationsSync methods."""

    module = None
    models_path = 'backends.sql'
    ignore_list = ['migrate_version']

    def setUp(self):
        super(ModelsMigrationsComparer, self).setUp()
        self.models_module = importlib.import_module(
            '.'.join((self.module, self.models_path)))

    def db_sync(self, engine):
        migration.db_sync(engine=engine,
                          abs_path=migration_helpers.find_migrate_repo(),
                          init_version=sql.migrate_repo.DB_INIT_VERSION)
        try:
            abs_path = migration_helpers.find_migrate_repo(
                importlib.import_module(self.module))
            migration.db_version_control(engine, abs_path)
            migration.db_sync(engine, abs_path)
        except exception.MigrationNotProvided:
            pass

    def include_object(self, object_, name, type_, reflected, compare_to):
        models = [m.__tablename__
                  for m in self.models_module.__dict__.values()
                  if inspect.isclass(m) and issubclass(m, sql.ModelBase)]

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
