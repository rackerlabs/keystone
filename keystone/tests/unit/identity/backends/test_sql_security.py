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


CONF = cfg.CONF


class SqlSecurityTests(object):
    driver = None  # subclasses must override driver to the actual driver.

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
        password = uuid.uuid4().hex
        user_dict = self._get_test_user_dict(password)
        # set password_created_at in the past
        password_created_at = (
            datetime.datetime.utcnow() -
            datetime.timedelta(days=10)
        )
        user = self._create_user(user_dict, password_created_at)
        CONF.security_compliance.password_expires_days = 1
        self.assertRaises(exception.PasswordExpired,
                          self.driver.authenticate,
                          user['id'],
                          password)
