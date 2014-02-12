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

from testtools import matchers

from keystone.common import utils
from keystone.tests import test_v3
from keystone.tests import utils as test_utils


class TestPasswordAuthenticaton(test_v3.RestfulTestCase):

    def setUp(self):
        super(TestPasswordAuthenticaton, self).setUp()
        self.user_ref = self.new_user_ref(domain_id=self.domain['id'])
        self.identity_api.create_user(self.user_ref['id'], self.user_ref)

    def _create_data(self, user_id, password, expires_at):
        return {
            'id': test_utils.new_uuid(),
            'user_id': user_id,
            'password': password,
            'expires_at': expires_at,
        }

    def get_request_token(self, password, expected_status):
        # TODO(dstanek): we may be able to move this up into common code and
        # replace other instances of this type of code...
        auth_data = self.build_authentication_request(
            user_id=self.user_ref['id'],
            password=password)
        r = self.post('/auth/tokens',
                      body=auth_data,
                      expected_status=expected_status)
        return r.headers.get('X-Subject-Token')

    def test_password_field_success(self):
        self.get_request_token(self.user_ref['password'], expected_status=201)

    def test_password_field_failure(self):
        self.get_request_token(test_utils.new_uuid(), expected_status=401)

    def test_rotated_password_success(self):
        # NOTE(dstanek): Create the rotated password directly using the CRUD.
        # This test is about testing the authentication and not the
        # rotation.
        password = test_utils.new_uuid()
        rotated_pw = self._create_data(self.user_ref['id'],
                                       utils.hash_password(password),
                                       test_utils.future_date())
        self.identity_api.create_rotated_password(rotated_pw)

        # normal password auth is working
        self.get_request_token(self.user_ref['password'], expected_status=201)

        # auth against a rotated password is working
        self.get_request_token(password, expected_status=201)

    def test_expired_rotated_password_fails(self):
        # NOTE(dstanek): Create the rotated password directly using the CRUD.
        # This test is about testing the authentication and not the
        # rotation.
        password = test_utils.new_uuid()
        rotated_pw = self._create_data(self.user_ref['id'],
                                       utils.hash_password(password),
                                       test_utils.past_date())
        self.identity_api.create_rotated_password(rotated_pw)

        # auth against a rotated password fails
        self.get_request_token(password, expected_status=401)

    def test_wrong_password_fails(self):
        # NOTE(dstanek): Create the rotated password directly using the CRUD.
        # This test is about testing the authentication and not the
        # rotation.
        hashed_password = utils.hash_password(test_utils.new_uuid())
        rotated_pw = self._create_data(self.user_ref['id'],
                                       hashed_password,
                                       test_utils.future_date())
        self.identity_api.create_rotated_password(rotated_pw)

        # the bad password won't match so this should fail
        bad_password = test_utils.new_uuid()
        self.get_request_token(test_utils.new_uuid(), expected_status=401)


class UserSelfServiceChangingPasswordsTestCase(test_v3.RestfulTestCase):

    def setUp(self):
        super(UserSelfServiceChangingPasswordsTestCase, self).setUp()
        self.user_ref = self.new_user_ref(domain_id=self.domain['id'])
        self.identity_api.create_user(self.user_ref['id'], self.user_ref)
        self.token = self.get_request_token(self.user_ref['password'], 201)

    def get_request_token(self, password, expected_status):
        # TODO(dstanek): we may be able to move this up into common code and
        # replace other instances of this type of code...
        auth_data = self.build_authentication_request(
            user_id=self.user_ref['id'],
            password=password)
        r = self.post('/auth/tokens',
                      body=auth_data,
                      expected_status=expected_status)
        return r.headers.get('X-Subject-Token')

    def change_password(self, expected_status, **kwargs):
        """Returns a test response for a change password request."""
        return self.post('/users/%s/password' % self.user_ref['id'],
                         body={'user': kwargs},
                         token=self.token,
                         expected_status=expected_status)

    def test_changing_password(self):
        # original password works
        self.get_request_token(self.user_ref['password'],
                               expected_status=201)

        # change password
        new_password = uuid.uuid4().hex
        self.change_password(password=new_password,
                             original_password=self.user_ref['password'],
                             expected_status=204)

        # old password fails
        self.get_request_token(self.user_ref['password'], expected_status=401)

        # new password works
        self.get_request_token(new_password, expected_status=201)

    def test_changing_password_with_missing_original_password_fails(self):
        r = self.change_password(password=uuid.uuid4().hex,
                                 expected_status=400)
        self.assertThat(r.result['error']['message'],
                        matchers.Contains('original_password'))

    def test_changing_password_with_missing_password_fails(self):
        r = self.change_password(original_password=self.user_ref['password'],
                                 expected_status=400)
        self.assertThat(r.result['error']['message'],
                        matchers.Contains('password'))

    def test_changing_password_with_incorrect_password_fails(self):
        self.change_password(password=uuid.uuid4().hex,
                             original_password=uuid.uuid4().hex,
                             expected_status=401)

    def test_changing_password_with_disabled_user_fails(self):
        # disable the user account
        self.user_ref['enabled'] = False
        self.patch('/users/%s' % self.user_ref['id'],
                   body={'user': self.user_ref})

        self.change_password(password=uuid.uuid4().hex,
                             original_password=self.user_ref['password'],
                             expected_status=401)

    def test_changing_password_disables_all_rotated_passwords(self):
        pass
