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

import datetime
import uuid

from oslo_config import cfg
from oslo_db.sqlalchemy import test_base as db_test

from keystone.common import sql
from keystone.identity.backends import sql as sql_backend
from keystone.tests.unit.identity.backends import test_base
from keystone.tests.unit.ksfixtures import database


CONF = cfg.CONF


class TestIdentityDriver(db_test.DbTestCase,
                         test_base.IdentityDriverV8Tests):

    expected_is_domain_aware = True
    expected_default_assignment_driver = 'sql'
    expected_is_sql = True
    expected_generates_uuids = True

    def setUp(self):
        super(TestIdentityDriver, self).setUp()

        # Set keystone's connection URL to be the test engine's url.
        database.initialize_sql_session(self.engine.url)

        # Override keystone's context manager to be oslo.db's global context
        # manager.
        sql.core._TESTING_USE_GLOBAL_CONTEXT_MANAGER = True
        self.addCleanup(setattr,
                        sql.core, '_TESTING_USE_GLOBAL_CONTEXT_MANAGER', False)
        self.addCleanup(sql.cleanup)

        version_specifiers = {}
        database._load_sqlalchemy_models(version_specifiers)
        sql.ModelBase.metadata.create_all(bind=self.engine)

        self.driver = sql_backend.Identity()


class MySQLOpportunisticIdentityDriverTestCase(TestIdentityDriver):
    FIXTURE = db_test.MySQLOpportunisticFixture


class PostgreSQLOpportunisticIdentityDriverTestCase(TestIdentityDriver):
    FIXTURE = db_test.PostgreSQLOpportunisticFixture


class AuthenticatorTests(object):
    def test_last_auth_date(self):
        # create user
        password = uuid.uuid4().hex
        user = {
            'name': uuid.uuid4().hex,
            'domain_id': CONF.identity.default_domain_id,
            'enabled': True,
            'password': password
        }
        user_created = self.identity_api.create_user(user)
        # authenticate, last_auth_at gets set here
        date_before = datetime.datetime.now()
        user_ret = sql_backend.Authenticator().authenticate(user_created['id'],
                                                            password)
        self.assertEqual(user_ret['id'], user_created['id'])
        date_after = datetime.datetime.now()
        # test last_auth_at, checking before/after to account for midnight
        user_ref = self._get_user_ref(user_created['id'])
        if date_before.date() != date_after.date():
            self.assertEqual(user_ref.local_user.last_auth_at.date(),
                             date_after.date())
        else:
            self.assertEqual(user_ref.local_user.last_auth_at.date(),
                             date_before.date())

    def _get_user_ref(self, user_id):
        with sql.session_for_read() as session:
            return self.identity_api._get_user(session, user_id)

    def test_user_disabled_due_to_inactivity(self):
        pass
