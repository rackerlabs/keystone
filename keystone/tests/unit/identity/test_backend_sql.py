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

import freezegun

from keystone.common import sql
from keystone.common import utils
import keystone.conf
from keystone import exception
from keystone.identity.backends import base
from keystone.identity.backends import sql_model as model
from keystone.tests.unit import test_backend_sql


CONF = keystone.conf.CONF


class DisableInactiveUserTests(test_backend_sql.SqlTests):
    def setUp(self):
        super(DisableInactiveUserTests, self).setUp()
        self.password = uuid.uuid4().hex
        self.user_dict = self._get_user_dict(self.password)
        self.max_inactive_days = 90
        self.config_fixture.config(
            group='security_compliance',
            disable_user_account_days_inactive=self.max_inactive_days)

    def test_authenticate_user_disabled_due_to_inactivity(self):
        # create user and set last_active_at beyond the max
        last_active_at = (
            datetime.datetime.utcnow() -
            datetime.timedelta(days=self.max_inactive_days + 1))
        user = self._create_user(self.user_dict, last_active_at.date())
        self.assertRaises(exception.UserDisabled,
                          self.identity_api.authenticate,
                          self.make_request(),
                          user_id=user['id'],
                          password=self.password)
        # verify that the user is actually disabled
        user = self.identity_api.get_user(user['id'])
        self.assertFalse(user['enabled'])
        # set the user to enabled and authenticate
        user['enabled'] = True
        self.identity_api.update_user(user['id'], user)
        user = self.identity_api.authenticate(self.make_request(),
                                              user_id=user['id'],
                                              password=self.password)
        self.assertTrue(user['enabled'])

    def test_authenticate_user_not_disabled_due_to_inactivity(self):
        # create user and set last_active_at just below the max
        last_active_at = (
            datetime.datetime.utcnow() -
            datetime.timedelta(days=self.max_inactive_days - 1)).date()
        user = self._create_user(self.user_dict, last_active_at)
        user = self.identity_api.authenticate(self.make_request(),
                                              user_id=user['id'],
                                              password=self.password)
        self.assertTrue(user['enabled'])

    def test_get_user_disabled_due_to_inactivity(self):
        user = self.identity_api.create_user(self.user_dict)
        # set last_active_at just beyond the max
        last_active_at = (
            datetime.datetime.utcnow() -
            datetime.timedelta(self.max_inactive_days + 1)).date()
        self._update_user(user['id'], last_active_at)
        # get user and verify that the user is actually disabled
        user = self.identity_api.get_user(user['id'])
        self.assertFalse(user['enabled'])
        # set enabled and test
        user['enabled'] = True
        self.identity_api.update_user(user['id'], user)
        user = self.identity_api.get_user(user['id'])
        self.assertTrue(user['enabled'])

    def test_get_user_not_disabled_due_to_inactivity(self):
        user = self.identity_api.create_user(self.user_dict)
        self.assertTrue(user['enabled'])
        # set last_active_at just below the max
        last_active_at = (
            datetime.datetime.utcnow() -
            datetime.timedelta(self.max_inactive_days - 1)).date()
        self._update_user(user['id'], last_active_at)
        # get user and verify that the user is still enabled
        user = self.identity_api.get_user(user['id'])
        self.assertTrue(user['enabled'])

    def test_enabled_after_create_update_user(self):
        self.config_fixture.config(group='security_compliance',
                                   disable_user_account_days_inactive=90)
        # create user without enabled; assert enabled
        del self.user_dict['enabled']
        user = self.identity_api.create_user(self.user_dict)
        user_ref = self._get_user_ref(user['id'])
        self.assertTrue(user_ref.enabled)
        now = datetime.datetime.utcnow().date()
        self.assertGreaterEqual(now, user_ref.last_active_at)
        # set enabled and test
        user['enabled'] = True
        self.identity_api.update_user(user['id'], user)
        user_ref = self._get_user_ref(user['id'])
        self.assertTrue(user_ref.enabled)
        # set disabled and test
        user['enabled'] = False
        self.identity_api.update_user(user['id'], user)
        user_ref = self._get_user_ref(user['id'])
        self.assertFalse(user_ref.enabled)
        # re-enable user and test
        user['enabled'] = True
        self.identity_api.update_user(user['id'], user)
        user_ref = self._get_user_ref(user['id'])
        self.assertTrue(user_ref.enabled)

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

    def _create_user(self, user_dict, last_active_at):
        user_dict['id'] = uuid.uuid4().hex
        user_dict = utils.hash_user_password(user_dict)
        with sql.session_for_write() as session:
            user_ref = model.User.from_dict(user_dict)
            user_ref.last_active_at = last_active_at
            session.add(user_ref)
            return base.filter_user(user_ref.to_dict())

    def _update_user(self, user_id, last_active_at):
        with sql.session_for_write() as session:
            user_ref = session.query(model.User).get(user_id)
            user_ref.last_active_at = last_active_at
            return user_ref


class LockingOutUserTests(test_backend_sql.SqlTests):
    def setUp(self):
        super(LockingOutUserTests, self).setUp()
        self.max_attempts = 6
        self.max_duration = 5
        self.config_fixture.config(
            group='security_compliance',
            lockout_failure_attempts=self.max_attempts)
        self.config_fixture.config(
            group='security_compliance',
            lockout_duration=self.max_duration)
        # setup user and passwords
        self.password = uuid.uuid4().hex
        self.wrong_password = uuid.uuid4().hex
        self.user = self._get_new_user(self.password)

    def test_locking_out_user_after_max_failed_attempts(self):
        # authenticate with wrong password
        self.assertRaises(AssertionError,
                          self.identity_api.authenticate,
                          self.make_request(),
                          user_id=self.user['id'],
                          password=self.wrong_password)
        # authenticate with right password
        self.identity_api.authenticate(self.make_request(),
                                       user_id=self.user['id'],
                                       password=self.password)
        # test locking out user after max failed attempts
        self._fail_auth(self.user['id'], self.wrong_password,
                        self.max_attempts)
        self.assertRaises(exception.AccountLocked,
                          self.identity_api.authenticate,
                          self.make_request(),
                          user_id=self.user['id'],
                          password=self.wrong_password)

    def test_set_enabled_unlocks_user(self):
        # lockout user
        self._fail_auth(self.user['id'], self.wrong_password,
                        self.max_attempts)
        self.assertRaises(exception.AccountLocked,
                          self.identity_api.authenticate,
                          self.make_request(),
                          user_id=self.user['id'],
                          password=self.wrong_password)
        # set enabled, user should be unlocked
        self.user['enabled'] = True
        self.identity_api.update_user(self.user['id'], self.user)
        user_ret = self.identity_api.authenticate(self.make_request(),
                                                  user_id=self.user['id'],
                                                  password=self.password)
        self.assertTrue(user_ret['enabled'])

    def test_lockout_duration(self):
        # freeze time
        time = datetime.datetime.now()
        with freezegun.freeze_time(time) as frozen_datetime:
            # lockout user
            self._fail_auth(self.user['id'], self.wrong_password,
                            self.max_attempts)
            self.assertRaises(exception.AccountLocked,
                              self.identity_api.authenticate,
                              self.make_request(),
                              user_id=self.user['id'],
                              password=self.wrong_password)
            # freeze time past the duration, user should be unlocked and failed
            # auth count should get reset
            frozen_datetime.tick(
                delta=datetime.timedelta(seconds=self.max_duration + 1))
            self.identity_api.authenticate(self.make_request(),
                                           user_id=self.user['id'],
                                           password=self.password)
            # test failed auth count was reset by authenticating with the wrong
            # password, should raise an assertion error and not account locked
            self.assertRaises(AssertionError,
                              self.identity_api.authenticate,
                              self.make_request(),
                              user_id=self.user['id'],
                              password=self.wrong_password)

    def test_lockout_duration_failed_auth_cnt_resets(self):
        # freeze time
        time = datetime.datetime.now()
        with freezegun.freeze_time(time) as frozen_datetime:
            # lockout user
            self._fail_auth(self.user['id'], self.wrong_password,
                            self.max_attempts)
            self.assertRaises(exception.AccountLocked,
                              self.identity_api.authenticate,
                              self.make_request(),
                              user_id=self.user['id'],
                              password=self.wrong_password)
            # freeze time past the duration, failed_auth_cnt should reset
            frozen_datetime.tick(
                delta=datetime.timedelta(seconds=self.max_duration + 1))
            # repeat failed auth the max times
            self._fail_auth(self.user['id'], self.wrong_password,
                            self.max_attempts)
            # test user account is locked
            self.assertRaises(exception.AccountLocked,
                              self.identity_api.authenticate,
                              self.make_request(),
                              user_id=self.user['id'],
                              password=self.wrong_password)

    def _fail_auth(self, user_id, wrong_password, attempts):
        for _ in range(attempts):
            self.assertRaises(AssertionError,
                              self.identity_api.authenticate,
                              self.make_request(),
                              user_id=user_id,
                              password=wrong_password)

    def _get_new_user(self, password):
        user = {
            'name': uuid.uuid4().hex,
            'domain_id': CONF.identity.default_domain_id,
            'enabled': True,
            'password': password
        }
        return self.identity_api.create_user(user)
