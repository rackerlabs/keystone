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

from oslo_config import cfg

from keystone import exception
from keystone.tests.unit import test_backend_sql


CONF = cfg.CONF


class LockingOutUserTests(test_backend_sql.SqlTests):
    def setUp(self):
        super(LockingOutUserTests, self).setUp()
        self.max_attempts = 6
        self.config_fixture.config(
            group='security_compliance',
            lockout_failure_attempts=self.max_attempts)
        self.config_fixture.config(
            group='security_compliance',
            lockout_duration=None)

    def test_locking_out_user_after_max_failed_attempts(self):
        password = uuid.uuid4().hex
        wrong_password = uuid.uuid4().hex
        user = self._get_new_user(password)
        # authenticate with wrong password
        self.assertRaises(AssertionError,
                          self.identity_api.authenticate,
                          context={},
                          user_id=user['id'],
                          password=wrong_password)
        # authenticate with right password
        user_ret = self.identity_api.authenticate(context={},
                                                  user_id=user['id'],
                                                  password=password)
        self.assertEqual(user['id'], user_ret['id'])
        # test locking out user after max failed attempts
        self._fail_auth(user['id'], wrong_password, self.max_attempts)
        self.assertRaises(exception.AccountLocked,
                          self.identity_api.authenticate,
                          context={},
                          user_id=user['id'],
                          password=wrong_password)

    def test_set_enabled_unlocks_user(self):
        password = uuid.uuid4().hex
        wrong_password = uuid.uuid4().hex
        user = self._get_new_user(password)
        # lockout user
        self._fail_auth(user['id'], wrong_password, self.max_attempts)
        self.assertRaises(exception.AccountLocked,
                          self.identity_api.authenticate,
                          context={},
                          user_id=user['id'],
                          password=wrong_password)
        # set enabled; user should be unlocked
        user['enabled'] = True
        self.identity_api.update_user(user['id'], user)
        user_ret = self.identity_api.authenticate(context={},
                                                  user_id=user['id'],
                                                  password=password)
        self.assertTrue(user_ret['enabled'])

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
