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

import importlib
import inspect

from oslo_db.sqlalchemy import test_base
from oslo_db.sqlalchemy import test_migrations
import testscenarios

from keystone.common import sql
from keystone.common.sql import migration_helpers
from keystone.tests.unit.ksfixtures import database

database.load_sqlalchemy_models()


class ModelsMigrationsComparer(object):

    """Mixin intended to override test_migrations.ModelsMigrationsSync methods.
    """

    scenarios = [(m, {'sql_module': m}) for m in database.get_sql_modules()]

    ignore_list = ['migrate_version']

    def get_engine(self):
        return self.engine

    def get_metadata(self):
        return sql.ModelBase.metadata

    def db_sync(self, engine):
        if 'contrib' in self.sql_module:
            # 'keystone.contrib.oauth1.backends.sql' -> 'oauth1'
            extension = self.sql_module.split('.')[-3]
        else:
            extension = None

        migration_helpers.sync_database_to_version(
            extension=extension, engine=self.get_engine())

    def _is_model(self, model):
        return inspect.isclass(model) and issubclass(model, sql.ModelBase)

    def include_object(self, object_, name, type_, reflected, compare_to):
        models_module = importlib.import_module(self.sql_module)
        module_items = models_module.__dict__.values()
        models = [i.__tablename__ for i in module_items if self._is_model(i)]

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
