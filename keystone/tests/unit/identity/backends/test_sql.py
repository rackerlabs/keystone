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

from oslo_db.sqlalchemy import enginefacade
from oslo_db.sqlalchemy import test_fixtures as db_fixtures
from oslotest import base as test_base

from keystone.common import sql
from keystone.identity.backends import sql as sql_backend
from keystone.tests.unit.identity.backends import test_base as id_test_base
from keystone.tests.unit.ksfixtures import database


class TestIdentityDriver(
    db_fixtures.OpportunisticDBTestMixin,
    test_base.BaseTestCase,
    id_test_base.IdentityDriverTests,
):

    expected_is_domain_aware = True
    expected_default_assignment_driver = 'sql'
    expected_is_sql = True
    expected_generates_uuids = True

    def setUp(self):
        super().setUp()

        # NOTE(stephenfin): this injects a new factory for each test and cleans
        # it up at then end of the test case. This way we can let each test
        # configure the factory so we can avoid having a global flag guarding
        # against factory re-configuration
        new_engine = enginefacade.transaction_context()
        new_engine.configure(sqlite_fk=True)
        self.useFixture(
            db_fixtures.ReplaceEngineFacadeFixture(
                sql.context_manager, new_engine,
            )
        )

        # Set keystone's connection URL to be the test engine's url. Close
        # sqlite FK to avoid conflicting with sql upgrade test.
        database.initialize_sql_session(enforce_sqlite_fks=False)

        self.engine = new_engine.writer.get_engine()

        database._load_sqlalchemy_models()
        sql.ModelBase.metadata.create_all(bind=self.engine)

        self.driver = sql_backend.Identity()


class MySQLOpportunisticIdentityDriverTestCase(TestIdentityDriver):
    FIXTURE = db_fixtures.MySQLOpportunisticFixture


class PostgreSQLOpportunisticIdentityDriverTestCase(TestIdentityDriver):
    FIXTURE = db_fixtures.PostgresqlOpportunisticFixture
