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

from keystone.common import sql
from keystone.common import utils
from keystone import exception
from keystone.identity.backends import base
from keystone.identity.backends import sql_model as model
from keystone.tests.unit import test_backend_sql


CONF = cfg.CONF


class PasswordExpiresValidationTests(test_backend_sql.SqlTests):
    def setUp(self):
        super(PasswordExpiresValidationTests, self).setUp()
        self.password = uuid.uuid4().hex
        self.user_dict = self._get_test_user_dict(self.password)
        self.password_expires_days = 90
        self.config_fixture.config(
            group='security_compliance',
            password_expires_days=self.password_expires_days)

    def test_authenticate_with_expired_password(self):
        # set password created_at so that the password will expire
        password_created_at = (
            datetime.datetime.utcnow() -
            datetime.timedelta(days=self.password_expires_days + 1)
        )
        user = self._create_user(self.user_dict, password_created_at)
        self.assertRaises(exception.PasswordExpired,
                          self.identity_api.authenticate,
                          context={},
                          user_id=user['id'],
                          password=self.password)

    def test_authenticate_with_non_expired_password(self):
        # set password created_at so that the password will not expire
        password_created_at = (
            datetime.datetime.utcnow() -
            datetime.timedelta(days=self.password_expires_days - 1)
        )
        user = self._create_user(self.user_dict, password_created_at)
        actual_user = self.identity_api.authenticate(context={},
                                                     user_id=user['id'],
                                                     password=self.password)
        self.assertEqual(user['id'], actual_user['id'])

    def test_authenticate_with_expired_password_for_ignore_user(self):
        # add the user id to the ignore list
        self.config_fixture.config(
            group='security_compliance',
            password_expires_ignore_list=self.user_dict['id'])
        # set password created_at so that the password will expire
        password_created_at = (
            datetime.datetime.utcnow() -
            datetime.timedelta(days=self.password_expires_days + 1)
        )
        user = self._create_user(self.user_dict, password_created_at)
        # verify the user can authenticate even though expired password
        user_ret = self.identity_api.authenticate(context={},
                                                  user_id=user['id'],
                                                  password=self.password)
        self.assertEqual(user['id'], user_ret['id'])

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
            user_ref.password_ref.created_at = password_created_at
            user_ref.password_ref.expires_at = (
                model.PasswordExpiresAtGetter().get(user_ref.id,
                                                    password_created_at))
            session.add(user_ref)
            return base.filter_user(user_ref.to_dict())
