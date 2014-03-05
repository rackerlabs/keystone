# Copyright 2014 Mirantis.inc
# All Rights Reserved.
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

"""Generate migration test cases.

Generate a uniform test cases to apply migrations sync and to test a models
for conformity with migrations and as a consequence with a database tables.
"""

import fnmatch
import importlib
import inspect
import os

from oslo_db.sqlalchemy import test_base
from oslo_db.sqlalchemy import test_migrations
import testscenarios

import keystone
from keystone.common import config
from keystone.common import sql
from keystone.common.sql import migration_helpers


def _get_sql_modules(paths=None):
    """Recursive get all modules and packages.

    This method works accordingly to an existing in Keystone naming
    convention: all sql models contained in a modules named `sql`.

    :keyword paths: list of paths of packages for further submodules search.
    :type paths: list
    :returns: list of Python paths for `sql` modules which contain sql models.
    """

    MODULES = []
    files = []

    KEYSTONE_PATH = keystone.__path__[0]

    for root, dirnames, filenames in os.walk(KEYSTONE_PATH):
        for filename in fnmatch.filter(filenames, 'sql.py'):
            # use relative root path, not absolute
            root = root.replace(KEYSTONE_PATH, 'keystone')
            files.append(os.path.join(root, filename))

    sql_modules = [f.replace('/', '.').strip('.py') for f in files]

    for module in sql_modules:
        if 'contrib' in module:
            # 'keystone.contrib.oauth1.backends.sql' -> 'oauth1'
            extension = module.split('.')[-3]
        else:
            extension = None

        MODULES.append((extension, module))

    return MODULES


def generate_scenarios():
    scenarios = []

    for extension, sql_module in _get_sql_modules():
        scenario_name = sql_module.replace('.', '_')

        scenario = {
            'sql_module': sql_module,
            'extension': extension,
            'models_module': importlib.import_module(sql_module),
        }

        scenarios.append((scenario_name, scenario))

    return scenarios


class ModelsMigrationsComparer(object):

    """Mixin intended to override test_migrations.ModelsMigrationsSync methods.
    """

    scenarios = generate_scenarios()
    ignore_list = ['migrate_version']

    def setUp(self):
        super(ModelsMigrationsComparer, self).setUp()
        config.configure()

    def get_engine(self):
        return self.engine

    def get_metadata(self):
        return sql.ModelBase.metadata

    def db_sync(self, engine):
        migration_helpers.sync_database_to_version(extension=self.extension,
                                                   engine=self.get_engine())

    def _is_model(self, model):
        return inspect.isclass(model) and issubclass(model, sql.ModelBase)

    def include_object(self, object_, name, type_, reflected, compare_to):
        modules = self.models_module.__dict__.values()
        models = [m.__tablename__ for m in modules if self._is_model(m)]

        if type_ == 'table':
            return name not in self.ignore_list and name in models
        return True


load_tests = testscenarios.load_tests_apply_scenarios


class TestModelsMigrationsSyncMySQL(ModelsMigrationsComparer,
                                    test_migrations.ModelsMigrationsSync,
                                    test_base.MySQLOpportunisticTestCase):

    pass


class TestModelsMigrationsSyncPostgreSQL(
        ModelsMigrationsComparer,
        test_migrations.ModelsMigrationsSync,
        test_base.PostgreSQLOpportunisticTestCase):

    pass
