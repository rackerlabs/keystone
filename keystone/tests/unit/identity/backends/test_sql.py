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
from keystone.common import utils
from keystone import exception
from keystone.identity.backends import base
from keystone.identity.backends import sql as sql_backend
from keystone.identity.backends import sql_model as model
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
    def test_user_disabled_due_to_inactivity(self):
        password = uuid.uuid4().hex
        user = self._get_user_dict(password)
        # create user and set last_auth_at beyond the max
        self.config_fixture.config(group='security_compliance',
                                   disable_user_account_days_inactive=90)
        last_active_at = (
            datetime.datetime.utcnow() - datetime.timedelta(days=91))
        user_create = (
            self._create_user_and_set_last_active_at(user, last_active_at))
        self.assertRaises(exception.UserDisabled,
                          sql_backend.Authenticator().authenticate,
                          user_create['id'],
                          password)
        # verify that the user is actually disabled
        user_found = self._get_user_ref(user_create['id'])
        self.assertFalse(user_found.enabled)

    def test_user_not_disabled_due_to_inactivity(self):
        password = uuid.uuid4().hex
        user = self._get_user_dict(password)
        # create user and set last_auth_at below the max
        self.config_fixture.config(group='security_compliance',
                                   disable_user_account_days_inactive=90)
        last_active_at = (
            datetime.datetime.utcnow() - datetime.timedelta(days=89))
        user_create = (
            self._create_user_and_set_last_active_at(user, last_active_at))
        user_auth = sql_backend.Authenticator().authenticate(user_create['id'],
                                                             password)
        self.assertTrue(user_auth['enabled'])

    def _get_user_dict(self, password):
        user = {
            'name': uuid.uuid4().hex,
            'domain_id': CONF.identity.default_domain_id,
            'enabled': True,
            'password': password
        }
        return user

    def _get_user_ref(self, user_id):
        with sql.session_for_read() as session:
            return session.query(model.User).get(user_id)

    def _create_user_and_set_last_active_at(self, user_dict, last_active_at):
        user_dict['id'] = uuid.uuid4().hex
        user_dict = utils.hash_user_password(user_dict)
        with sql.session_for_write() as session:
            user_ref = model.User.from_dict(user_dict)
            user_ref.last_active_at = last_active_at
            session.add(user_ref)
            return base.filter_user(user_ref.to_dict())
