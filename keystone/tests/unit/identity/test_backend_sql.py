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

import keystone.conf
from keystone import exception
from keystone.tests.unit import test_backend_sql


CONF = keystone.conf.CONF


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
                          context={},
                          user_id=self.user['id'],
                          password=self.wrong_password)
        # authenticate with right password
        user_ret = self.identity_api.authenticate(context={},
                                                  user_id=self.user['id'],
                                                  password=self.password)
        self.assertEqual(self.user['id'], user_ret['id'])
        # test locking out user after max failed attempts
        self._fail_auth(self.user['id'], self.wrong_password,
                        self.max_attempts)
        self.assertRaises(exception.AccountLocked,
                          self.identity_api.authenticate,
                          context={},
                          user_id=self.user['id'],
                          password=self.wrong_password)

    def test_set_enabled_unlocks_user(self):
        # lockout user
        self._fail_auth(self.user['id'], self.wrong_password,
                        self.max_attempts)
        self.assertRaises(exception.AccountLocked,
                          self.identity_api.authenticate,
                          context={},
                          user_id=self.user['id'],
                          password=self.wrong_password)
        # set enabled; user should be unlocked
        self.user['enabled'] = True
        self.identity_api.update_user(self.user['id'], self.user)
        user_ret = self.identity_api.authenticate(context={},
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
                              context={},
                              user_id=self.user['id'],
                              password=self.wrong_password)
            # freeze time past the duration, user should be unlocked
            frozen_datetime.tick(
                delta=datetime.timedelta(seconds=self.max_duration + 1))
            user_ret = self.identity_api.authenticate(context={},
                                                      user_id=self.user['id'],
                                                      password=self.password)
            self.assertEqual(self.user['id'], user_ret['id'])
            # authenticate with wrong password, test fail auth cnt gets reset
            self.assertRaises(AssertionError,
                              self.identity_api.authenticate,
                              context={},
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
                              context={},
                              user_id=self.user['id'],
                              password=self.wrong_password)
            # freeze time past the duration, failed_auth_cnt should reset
            frozen_datetime.tick(
                delta=datetime.timedelta(seconds=self.max_duration + 1))
            # lockout user again, but failing auth max times
            self._fail_auth(self.user['id'], self.wrong_password,
                            self.max_attempts)
            self.assertRaises(exception.AccountLocked,
                              self.identity_api.authenticate,
                              context={},
                              user_id=self.user['id'],
                              password=self.wrong_password)

    def _fail_auth(self, user_id, wrong_password, attempts):
        for _ in range(attempts):
            self.assertRaises(AssertionError,
                              self.identity_api.authenticate,
                              context={},
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
