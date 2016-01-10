# Copyright 2015 UnitedStack, Inc
#
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

from six.moves import http_client

from keystone.common import utils
from keystone.contrib.ec2 import controllers
from keystone.tests import unit
from keystone.tests.unit import rest


CRED_TYPE_EC2 = controllers.CRED_TYPE_EC2


class TestCredentialEc2(rest.RestfulTestCase):
    def setUp(self):
        super(TestCredentialEc2, self).setUp()
        self.user_id = self.user_foo['id']
        self.project_id = self.tenant_bar['id']

    def _get_token_id(self, r):
        return r.result['access']['token']['id']

    def _get_ec2_cred(self):
        uri = self._get_ec2_cred_uri()
        r = self.public_request(method='POST', token=self.get_scoped_token(),
                                path=uri, body={'tenant_id': self.project_id})
        return r.result['credential']

    def _get_ec2_cred_uri(self):
        return '/v2.0/users/%s/credentials/OS-EC2' % self.user_id

    def test_ec2_cannot_get_non_ec2_credential(self):
        access_key = uuid.uuid4().hex
        cred_id = utils.hash_access_key(access_key)
        non_ec2_cred = unit.new_credential_ref(
            user_id=self.user_id,
            project_id=self.project_id)
        non_ec2_cred['id'] = cred_id
        self.credential_api.create_credential(cred_id, non_ec2_cred)

        # if access_key is not found, ec2 controller raises Unauthorized
        # exception
        path = '/'.join([self._get_ec2_cred_uri(), access_key])
        self.public_request(method='GET', token=self.get_scoped_token(),
                            path=path,
                            expected_status=http_client.UNAUTHORIZED)

    def test_ec2_list_credentials(self):
        self._get_ec2_cred()
        uri = self._get_ec2_cred_uri()
        r = self.public_request(method='GET', token=self.get_scoped_token(),
                                path=uri)
        cred_list = r.result['credentials']
        self.assertEqual(1, len(cred_list))

    def test_ec2_cannot_list_non_ec2_credentials(self):
        non_ec2_cred = unit.new_credential_ref(
            user_id=self.user_id,
            project_id=self.project_id)
        non_ec2_cred['type'] = uuid.uuid4().hex
        self.credential_api.create_credential(non_ec2_cred['id'], non_ec2_cred)
        uri = self._get_ec2_cred_uri()
        r = self.public_request(method='GET', token=self.get_scoped_token(),
                                path=uri)
        cred_list_2 = r.result['credentials']
        # non-EC2 credentials are not returned.
        self.assertEqual(0, len(cred_list_2))

        # add an EC2 credential
        self._get_ec2_cred()
        r = self.public_request(method='GET', token=self.get_scoped_token(),
                                path=uri)
        cred_list = r.result['credentials']
        self.assertEqual(1, len(cred_list))
