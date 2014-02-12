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

from testtools import matchers

from keystone import config
from keystone.tests import test_v3
from keystone.tests import utils


CONF = config.CONF


class TestPasswordRotationApi(test_v3.RestfulTestCase):

    EXTENSION_TO_ADD = 'password_rotation_extension'

    def setUp(self):
        super(TestPasswordRotationApi, self).setUp()
        self.user_ref = self.new_user_ref(domain_id=self.domain['id'])
        self.identity_api.create_user(self.user_ref['id'], self.user_ref)
        self.token = self.get_request_token(self.user_ref['password'], 201)
        self.original_password = self.user_ref['password']

    def get_request_token(self, password, expected_status):
        auth_data = self.build_authentication_request(
            username=self.user_ref['name'],
            user_domain_id=self.domain['id'],
            password=password)
        r = self.post('/auth/tokens', body=auth_data,
                      expected_status=expected_status)
        return r.headers.get('X-Subject-Token')

    def rotate_password(self, expected_status, **kwargs):
        """Returns a test response for a rotate password request."""
        path = '/users/%s/OS-PW-ROTATE/passwords' % self.user_ref['id']
        return self.post(path,
                         body={'user': kwargs},
                         token=self.token,
                         expected_status=expected_status)

    def expire_old_passwords(self):
        """Returns a test response for a rotate password request."""
        token = self.get_request_token(self.new_password, 201)
        path = ('/users/%s/OS-PW-ROTATE/old_passwords' %
                self.user_ref['id'])
        return self.delete(path, token=token)

    def _test_rotating_password(self):
        # original password works
        self.get_request_token(self.original_password, expected_status=201)

        # rotate password
        self.new_password = utils.new_uuid()
        self.rotate_password(password=self.new_password,
                             original_password=self.original_password,
                             expected_status=204)

        # original password still works
        self.get_request_token(self.original_password, expected_status=201)

        # new password works
        self.get_request_token(self.new_password, expected_status=201)

    def test_rotating_password_where_old_password_is_not_yet_expired(self):
        # NOTE(dstanek): this is the common case where a password is
        # rotated and both the old and new work for a short period of
        # time
        self._test_rotating_password()

    def test_rotating_password_where_old_password_is_expired(self):
        self._test_rotating_password()

        self.expire_old_passwords()

        # original password now fails
        self.get_request_token(self.original_password, expected_status=401)

        # new password still works
        self.get_request_token(self.new_password, expected_status=201)

    def test_rotating_password_with_missing_original_password_fails(self):
        r = self.rotate_password(password=utils.new_uuid(),
                                 expected_status=400)
        self.assertThat(r.result['error']['message'],
                        matchers.Contains('original_password'))

    def test_rotating_password_with_missing_password_fails(self):
        r = self.rotate_password(original_password=self.user_ref['password'],
                                 expected_status=400)
        self.assertThat(r.result['error']['message'],
                        matchers.Contains('password'))

    def test_rotating_password_with_incorrect_password_fails(self):
        self.rotate_password(password=utils.new_uuid(),
                             original_password=utils.new_uuid(),
                             expected_status=401)

    def test_rotating_password_with_disabled_user_fails(self):
        # disable the user account
        self.user_ref['enabled'] = False
        self.patch('/users/%s' % self.user_ref['id'],
                   body={'user': self.user_ref})

        self.rotate_password(password=utils.new_uuid(),
                             original_password=self.user_ref['password'],
                             expected_status=401)
