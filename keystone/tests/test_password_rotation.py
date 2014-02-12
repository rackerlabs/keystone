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

from oslo.config import cfg
from testtools import matchers

from keystone.common import controller
from keystone import exception
from keystone import tests
from keystone.tests import test_v3


CONF = cfg.CONF


class RotatingPasswordsTestCase(test_v3.RestfulTestCase):
    EXTENSION_TO_ADD = 'password_rotation_extension'

    def setUp(self):
        super(UserSelfServiceRotatingPasswordsTestCase, self).setUp()
        self.user_ref = self.new_user_ref(domain_id=self.domain['id'])
        self.identity_api.create_user(self.user_ref['id'], self.user_ref)
        self.token = self.get_request_token(self.user_ref['password'], 201)

    def get_request_token(self, password, expected_status):
        auth_data = self.build_authentication_request(
            user_id=self.user_ref['id'],
            password=password)
        r = self.post('/auth/tokens',
                      body=auth_data,
                      expected_status=expected_status)
        return r.headers.get('X-Subject-Token')

    def rotate_password(self, expected_status, **kwargs):
        """Returns a test response for a change password request."""
        path = '/users/%s/OS-PW-ROTATE/password' % self.user_ref['id']
        return self.post(path,
                         body={'user': kwargs},
                         token=self.token,
                         expected_status=expected_status)

#    def test_rotation(self):


    def Xtest_simple_rotating_passwords(self):
        # original password works
        self.get_request_token(self.user_ref['password'],
                               expected_status=201)

        # change password
        new_password = uuid.uuid4().hex
        self.rotate_password(password=new_password,
                             original_password=self.user_ref['password'],
                             expected_status=204)
#
#        # original password still works
#        self.get_request_token(self.user_ref['password'],
#                               expected_status=201)
#
#        # new password works
#        self.get_request_token(new_password, expected_status=201)

    def Xtest_old_password_after_expiration(self):
        pass

    def Xtest_manually_expiring_old_password(self):

        # original password works
        self.get_request_token(self.user_ref['password'],
                               expected_status=201)

        # change password
        new_password = uuid.uuid4().hex
        self.rotate_password(password=new_password,
                             original_password=self.user_ref['password'],
                             expected_status=204)

        # expire old passwords
        self.delete('/users/%s/OS-PW-ROTATE/old_passwords' %
                    self.user_ref['id'])

        # original password still works
        self.get_request_token(self.user_ref['password'],
                               expected_status=201)

        # new password works
        self.get_request_token(new_password, expected_status=201)
