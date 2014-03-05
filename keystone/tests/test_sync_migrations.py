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

"""Generate migration test cases.

Generate a uniform test cases to apply migrations sync and to test a models
for conformity with migrations and as a consequence with a database tables.
Used a following naming convention for generated test cases:
Test<CapitalizeDriverName><CapitalizedMergedPath>.
A module path used in a test class name is composed in the following
way: used only meaningful (unique) part of the path, removed all dots and
underscores, resulting parts capitalized and merged. To call a particular test
case you should use a generated class name as normal test case name. Expected
class name example:
    TestMySQLContribEndpointFilter
This means that a backends.sql module lies in the
keystone.contrib.endpoint_filter directory.
"""

import importlib
import inspect
import itertools
import os
import pkgutil
import re

from oslo.db.sqlalchemy import test_base
from oslo.db.sqlalchemy import test_migrations

import keystone
from keystone.common import sql
from keystone.common.sql import migration_helpers


MODULES = []
BACKENDS = (test_base.PostgreSQLOpportunisticTestCase,
            test_base.MySQLOpportunisticTestCase)


class ModelsMigrationsComparer(test_base.DbTestCase):

    """Mixin intended to override test_migrations.ModelsMigrationsSync methods.
    """

    sql_module = None
    extension = None
    ignore_list = ['migrate_version']

    def setUp(self):
        super(ModelsMigrationsComparer, self).setUp()
        self.models_module = importlib.import_module(self.sql_module)

    def db_sync(self, engine):
        migration_helpers.sync_database_to_version(extension=self.extension,
                                                   engine=self.get_engine())

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


def _append_modules(modules_list):
    """Check for sql modules and append to a list.

    This method works accordingly to an existing in Keystone naming
    convention: all sql models contained in a modules named `sql`.
    """

    for importer, mod_name, ispkg in modules_list:
        if mod_name == 'sql':
            module = os.path.relpath(importer.path).split('/')
            sql_module = '.'.join(module + [mod_name, ])
            extension = module[-2] if 'contrib' in module else None

            MODULES.append((extension, sql_module))


def _separate_packages_modules(modules):
    return (filter(lambda m: m[2], modules),
            filter(lambda m: not m[2], modules))


def _get_sql_modules(paths=None):
    """Recursive get all modules and packages.

    :keyword paths: list of paths of packages for further submodules search.
    :type paths: list
    :returns: list of Python paths for `sql` modules which contain sql models.
    """

    paths = keystone.__path__ if not paths and not MODULES else paths
    if not paths:
        return MODULES

    # NOTE(I159): pkgutil.walk_packages takes list of paths but if
    # submodules have the same name only one of them will be in return data.
    all_modules = itertools.chain(
        *[pkgutil.walk_packages([i, ]) for i in paths])

    regexp = re.compile('hacking|tests|common\.*\w*')
    all_modules = filter(lambda p: not regexp.search(p[1]), all_modules)
    packs, modules = _separate_packages_modules(all_modules)

    _append_modules(modules)
    paths = ['/'.join([p[0].path, p[1]]) for p in packs]

    return _get_sql_modules(paths)


def _generate_test_cases():
    """Create specific test cases for every combination of a mod and backend.

    To test all the modules with all the backends necessary to implement a
    number of almost identical test cases. The fabric function produces all
    necessary test cases and puts it to a global module namespace. This
    approach helps to keep the module DRY.
    """

    bases = ModelsMigrationsComparer, test_migrations.ModelsMigrationsSync

    for bc in BACKENDS:
        bc_name = bc.__name__.replace('OpportunisticTestCase', '')
        nc_bases = bases + (bc, )

        for extension, sql_module in _get_sql_modules():
            md_name = ''.join(
                (m.capitalize() for m in re.split('\.|_', sql_module)[1:-1])
            )
            name = ''.join(('Test', bc_name, md_name))
            globals()[name] = type(name,
                                   nc_bases,
                                   {'sql_module': sql_module,
                                    'extension': extension})


_generate_test_cases()
