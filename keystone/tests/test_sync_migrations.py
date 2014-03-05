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

import copy
import importlib
import inspect

import six

from keystone.common import sql
from keystone.common.sql import migration_helpers
from keystone import exception
from keystone.openstack.common.db.sqlalchemy import migration
from keystone.openstack.common.db.sqlalchemy import test_base
from keystone.openstack.common.db.sqlalchemy import test_migrations


class RealBackends(object):
    """Meta class produces test cases for all required modules and backends

    Attributes
    ::backends: basic test cases to use real backends for testing.
    ::modules: relative paths to modules containing sqlalchemy models.

    To test all the modules with all the backends necessary to implement amount
    of almost identical test cases. The meta calss produces all neccessary
    test cases and puts it to a global module namespace. This approach helps
    to keep the module DRY.
    """

    backends = (test_base.PostgreSQLOpportunisticTestCase,
                test_base.MySQLOpportunisticTestCase)
    modules = ('trust',
               'identity',
               'contrib.oauth1',
               'contrib.federation',
               'contrib.endpoint_filter',
               'token',
               'assignment',
               'credential',
               'policy',
               'catalog',
               'catalog')

    @classmethod
    def _produce(cls, bases, attrs):
        """Uses all real backends for all modules containing sqlalchemy models.
        """
        for bc in cls.backends:
            bc_name = bc.__name__.replace('OpportunisticTestCase', '')
            nc_bases = list(bases)
            nc_bases.insert(0, bc)

            for module in cls.modules:
                md_name = module.split('.')[-1].capitalize()
                name = ''.join(('Test', bc_name, md_name))
                nc_attrs = copy.copy(attrs)
                nc_attrs['module'] = '.'.join(('keystone', module))
                yield (name, type(name, tuple(nc_bases), attrs))

    def __new__(cls, name, bases, attrs):
        """Push all created modules to a global modules namespace

        The class itself does not contain any tests.
        """
        globals().update(dict(cls._produce(bases, attrs)))
        return type(name, tuple(), {})


class LoaderSynchronizer(test_base.DbTestCase):
    """Mixin intended to override ModelsMigrationsSync methods."""

    module = None
    models_path = 'backends.sql'
    ignore_list = ['migrate_version', ]

    def setUp(self):
        super(LoaderSynchronizer, self).setUp()
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


@six.add_metaclass(RealBackends)
class TestSyncModelsMigrations(LoaderSynchronizer,
                               test_migrations.ModelsMigrationsSync):
    pass
