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


import uuid

from oslo_db.sqlalchemy import test_base as db_test

from keystone.common import sql
from keystone import exception
from keystone.identity.backends import sql as sql_backend
from keystone.tests.unit.identity.backends import test_base
from keystone.tests.unit.ksfixtures import database


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


class PasswordHistoryValidatorTests(object):
    def test_validate_invalid_password(self):
        self.config_fixture.config(group='security_compliance',
                                   unique_last_password_count=4)
        user = self._create_user('mypassword1')
        user['password'] = 'mypassword2'
        user_ret = self.identity_api.update_user(user['id'], user)
        self.assertEqual(user['id'], user_ret['id'])
        user['password'] = 'mypassword3'
        user_ret = self.identity_api.update_user(user['id'], user)
        self.assertEqual(user['id'], user_ret['id'])
        # attempt to update password matching the 2nd password
        user['password'] = 'mypassword2'
        self.assertRaises(exception.PasswordValidationError,
                          self.identity_api.update_user,
                          user['id'],
                          user)

    def test_password_history_for_user_with_no_password(self):
        self.config_fixture.config(group='security_compliance',
                                   unique_last_password_count=2)
        password = None
        user = self._create_user(password)
        user_ref = self._get_user_ref(user['id'])
        self.assertIsNone(user_ref.password)
        user['password'] = 'mypassword2'
        self.identity_api.update_user(user['id'], user)
        user_ref = self._get_user_ref(user['id'])
        first_password = user_ref.password
        self.assertIsNotNone(user_ref.password)
        user['password'] = 'mypassword3'
        self.identity_api.update_user(user['id'], user)
        user_ref = self._get_user_ref(user['id'])
        self.assertIsNotNone(user_ref.password)
        second_password = user_ref.password
        self.assertNotEqual(first_password, second_password)

    def test_truncate_passwords(self):
        max_cnt = 2
        self.config_fixture.config(group='security_compliance',
                                   unique_last_password_count=max_cnt)
        user = self._create_user(uuid.uuid4().hex)
        self._add_passwords(user, 4)
        user_ref = self._get_user_ref(user['id'])
        self.assertTrue(len(user_ref.local_user.passwords) == (max_cnt + 1))

    def test_truncate_passwords_when_max_is_zero(self):
        expected_length = 2
        max_cnt = 0
        self.config_fixture.config(group='security_compliance',
                                   unique_last_password_count=max_cnt)
        user = self._create_user(uuid.uuid4().hex)
        self._add_passwords(user, 4)
        user_ref = self._get_user_ref(user['id'])
        self.assertTrue(len(user_ref.local_user.passwords) == expected_length)
        # start with multiple passwords and then change max_cnt to zero
        max_cnt = 4
        self.config_fixture.config(group='security_compliance',
                                   unique_last_password_count=max_cnt)
        self._add_passwords(user, max_cnt)
        user_ref = self._get_user_ref(user['id'])
        self.assertTrue(len(user_ref.local_user.passwords) == (max_cnt + 1))
        max_cnt = 0
        self.config_fixture.config(group='security_compliance',
                                   unique_last_password_count=max_cnt)
        self._add_passwords(user, 1)
        user_ref = self._get_user_ref(user['id'])
        self.assertTrue(len(user_ref.local_user.passwords) == expected_length)

    def _create_user(self, password):
        user = {
            'name': uuid.uuid4().hex,
            'domain_id': 'default',
            'enabled': True,
            'password': password
        }
        return self.identity_api.create_user(user)

    def _add_passwords(self, user, n):
        count = 0
        while (count < n):
            user['password'] = uuid.uuid4().hex
            self.identity_api.update_user(user['id'], user)
            count += 1

    def _get_user_ref(self, user_id):
        with sql.session_for_read() as session:
            return self.identity_api._get_user(session, user_id)
