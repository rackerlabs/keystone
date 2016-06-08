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
    def _get_test_user_dict(self, password):
        test_user_dict = {
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex,
            'domain_id': 'default',
            'enabled': True,
            'password': password
        }
        return test_user_dict

    def _create_user(self, user_dict, password_created_at):
        user_dict = utils.hash_user_password(user_dict)
        with sql.session_for_write() as session:
            user_ref = model.User.from_dict(user_dict)
            user_ref = self._override_password_created_at(user_ref,
                                                          password_created_at)
            session.add(user_ref)
            return base.filter_user(user_ref.to_dict())

    def _override_password_created_at(self, user_ref, password_created_at):
        for password_ref in user_ref.local_user.passwords:
            if not password_ref.expired:
                password_ref.created_at = password_created_at
        return user_ref

    def test_authenticate_with_expired_password(self):
        self.config_fixture.config(group='security_compliance',
                                   password_expires_days=90)
        password = uuid.uuid4().hex
        user_dict = self._get_test_user_dict(password)
        # set password created_at so that the password will expire
        password_created_at = (
            datetime.datetime.utcnow() -
            datetime.timedelta(days=91)
        )
        user = self._create_user(user_dict, password_created_at)
        self.assertRaises(exception.PasswordExpired,
                          sql_backend.Authenticator().authenticate,
                          user['id'],
                          password)

    def test_authenticate_with_non_expired_password(self):
        self.config_fixture.config(group='security_compliance',
                                   password_expires_days=90)
        password = uuid.uuid4().hex
        user_dict = self._get_test_user_dict(password)
        # set password created_at so that the password will not expire
        password_created_at = (
            datetime.datetime.utcnow() -
            datetime.timedelta(days=89)
        )
        user = self._create_user(user_dict, password_created_at)
        actual_user = sql_backend.Authenticator().authenticate(user['id'],
                                                               password)
        self.assertEqual(user['id'], actual_user['id'])

    def test_authenticate_with_expired_password_for_ignore_user(self):
        self.config_fixture.config(group='security_compliance',
                                   password_expires_days=90)
        password = uuid.uuid4().hex
        user_dict = self._get_test_user_dict(password)
        # set password created_at so that the password will expire
        password_created_at = (
            datetime.datetime.utcnow() -
            datetime.timedelta(days=91)
        )
        user = self._create_user(user_dict, password_created_at)
        self.assertRaises(exception.PasswordExpired,
                          sql_backend.Authenticator().authenticate,
                          user['id'],
                          password)
        # add user to ignore list and confirm password is no longer expired
        self.config_fixture.config(group='security_compliance',
                                   password_expires_ignore_list=user['id'])
        ret_user = sql_backend.Authenticator().authenticate(user['id'],
                                                            password)
        self.assertEqual(user['id'], ret_user['id'])

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


class PasswordHistoryValidatorTests(object):
    def test_validate_invalid_password(self):
        self.config_fixture.config(group='security_compliance',
                                   unique_last_password_count=4)
        user = {
            'name': uuid.uuid4().hex,
            'domain_id': CONF.identity.default_domain_id,
            'enabled': True,
            'password': 'mypassword1'
        }
        user = self.identity_api.create_user(user)
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
