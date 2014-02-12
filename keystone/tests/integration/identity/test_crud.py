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

from keystone.identity.backends import sql
from keystone import tests


def future_date():
    """Returns a datetime representing a date 24hrs in the future."""
    return datetime.datetime.utcnow() + datetime.timedelta(hours=24)


def past_date():
    """Returns a datetime representing a date 24hrs in the past."""
    return datetime.datetime.utcnow() - datetime.timedelta(hours=24)


class TestPasswordRotationCrudSQL(tests.TestCase):

    def setUp(self):
        super(TestPasswordRotationCrudSQL, self).setUp()
        self.driver = sql.Identity()
        tests.setup_database()
        self.addCleanup(tests.teardown_database)

        # create the sample data

        self.user_id = tests.new_id()

        future_rp = self._create_data(self.user_id, future_date())
        self.future_rp = self.driver.create_rotated_password(future_rp)

        past_rp = self._create_data(self.user_id, past_date())
        self.past_rp = self.driver.create_rotated_password(past_rp)

    def _create_data(self, user_id, expires_at):
        return {
            'id': tests.new_id(),
            'user_id': user_id,
            'password': tests.new_id(),
            'expires_at': expires_at,
        }

    def test_retrieving_all_rotated_passwords(self):
        rotated_passwords = self.driver.list_rotated_passwords_by_user(
            self.user_id, None)
        self.assertEqual(len(rotated_passwords), 2)
        self.assertIn(self.future_rp, rotated_passwords)
        self.assertIn(self.past_rp, rotated_passwords)

    def test_retrieving_active_rotated_passwords(self):
        rotated_passwords = self.driver.list_active_rotated_passwords_by_user(
            self.user_id, None)
        self.assertEqual(len(rotated_passwords), 1)
        self.assertIn(self.future_rp, rotated_passwords)

    def test_deleting_expired_rotated_passwords(self):
        # create another user's data to make sure we don't delete it too
        other_user_id = tests.new_id()
        other_user_rp = self._create_data(other_user_id, past_date())
        other_user_rp = self.driver.create_rotated_password(other_user_rp)

        # do the delete
        self.driver.delete_expired_rotated_passwords_by_user(self.user_id)
        rotated_passwords = self.driver.list_rotated_passwords_by_user(
            self.user_id, None)
        self.assertEqual(len(rotated_passwords), 1)
        self.assertIn(self.future_rp, rotated_passwords)

        # assert the other user's data is still there
        rotated_passwords = self.driver.list_rotated_passwords_by_user(
            other_user_id, None)
        self.assertEqual(len(rotated_passwords), 1)
        self.assertIn(other_user_rp, rotated_passwords)
