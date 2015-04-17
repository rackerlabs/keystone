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

import mock
from oslo_db.sqlalchemy import test_base
from oslo_db.sqlalchemy import test_migrations
import testscenarios

from keystone.common import sql
from keystone.common.sql import migration_helpers
from keystone.tests.unit.ksfixtures import database

database.load_sqlalchemy_models()

IGNORED_SCENARIOS = [
    # FIXME(viktors): Enable this scenario, when patch
    # https://review.openstack.org/#/c/174388/ lands.
    'keystone.contrib.endpoint_filter.backends.sql',
    # FIXME(viktors): Enable this scenario, when patch
    # https://review.openstack.org/#/c/168947 lands.
    'keystone.contrib.federation.backends.sql',
    # FIXME(viktors): Fix errors and enable this scenario
    'keystone.contrib.revoke.backends.sql',
]


class ModelsMigrationsComparer(object):
    """Mixin intended to override migrations.ModelsMigrationsSync methods."""

    scenarios = [(m, {'sql_module': m}) for m in database.get_sql_modules()
                 if m not in IGNORED_SCENARIOS]

    ignore_list = ['migrate_version']

    def setUp(self):
        # TODO(viktors): remove this method, when patch
        # https://review.openstack.org/#/c/137778/ will be merged
        super(ModelsMigrationsComparer, self).setUp()

        get_engine_mock = mock.patch.object(sql, 'get_engine',
                                            return_value=self.engine)
        get_engine_mock.start()
        self.addCleanup(get_engine_mock.stop)

    def get_engine(self):
        return self.engine

    def get_metadata(self):
        return sql.ModelBase.metadata

    def db_sync(self, engine):
        extension = None

        for default_extension in migration_helpers.DEFAULT_EXTENSIONS:
            if default_extension in self.sql_module:
                extension = default_extension
                break

        migration_helpers.sync_database_to_version(extension=extension)

    def _is_model(self, model):
        return inspect.isclass(model) and issubclass(model, sql.ModelBase)

    def _get_models(self):
        models_module = importlib.import_module(self.sql_module)
        module_items = models_module.__dict__.values()
        return [i.__tablename__ for i in module_items if self._is_model(i)]

    def include_object(self, object_, name, type_, reflected, compare_to):
        """Return True for objects that should be compared

        This method re-defined, because we need ignore tables, defined in the
        another `sql` modules. So in the each test we should get list of models
        defined in module and check only them.
        """
        if type_ == 'table':
            if name in self.ignore_list:
                # ignore service tables
                return False

            return name in self._get_models()

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
