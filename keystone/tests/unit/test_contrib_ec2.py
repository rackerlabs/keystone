# Copyright 2015 Intel Corporation
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

from keystoneclient.contrib.ec2 import utils as ec2_utils

from keystone.contrib.ec2 import controllers
from keystone import exception
from keystone.tests import unit as tests
from keystone.tests.unit import default_fixtures
from keystone.tests.unit.ksfixtures import database


class TestCredentialEc2(tests.TestCase):
    # TODO(Dave Chen): more testcase for ec2 credential is expected here and
    # the file name would be renamed to "test_credential" to correspond with
    # "test_v3_credential.py" in the future. testcase set up here only intends
    # for verification against bug #1289115.
    def setUp(self):
        super(TestCredentialEc2, self).setUp()
        self.useFixture(database.Database())
        self.load_backends()
        self.load_fixtures(default_fixtures)
        self.user_id = self.user_foo['id']
        self.project_id = self.tenant_bar['id']
        self.blob = {"access": uuid.uuid4().hex,
                     "secret": uuid.uuid4().hex}
        self.controller = controllers.Ec2Controller()
        self.creds_ref = {'user_id': self.user_id,
                          'tenant_id': self.project_id,
                          'access': self.blob['access'],
                          'secret': self.blob['secret'],
                          'trust_id': None}

    def test_signature_validate_no_host_port(self):
        """Test signature validation with the access/secret provided."""
        access = self.blob['access']
        secret = self.blob['secret']
        signer = ec2_utils.Ec2Signer(secret)
        params = {'SignatureMethod': 'HmacSHA256',
                  'SignatureVersion': '2',
                  'AWSAccessKeyId': access}
        request = {'host': 'foo',
                   'verb': 'GET',
                   'path': '/bar',
                   'params': params}
        signature = signer.generate(request)

        sig_ref = {'access': access,
                   'signature': signature,
                   'host': 'foo',
                   'verb': 'GET',
                   'path': '/bar',
                   'params': params}

        # Now validate the signature based on the dummy request
        self.assertTrue(self.controller.check_signature(self.creds_ref,
                                                        sig_ref))

    def test_signature_validate_with_host_port(self):
        """Test signature validation when host is bound with port."""
        access = self.blob['access']
        secret = self.blob['secret']
        signer = ec2_utils.Ec2Signer(secret)
        params = {'SignatureMethod': 'HmacSHA256',
                  'SignatureVersion': '2',
                  'AWSAccessKeyId': access}
        request = {'host': 'foo:8080',
                   'verb': 'GET',
                   'path': '/bar',
                   'params': params}
        signature = signer.generate(request)

        sig_ref = {'access': access,
                   'signature': signature,
                   'host': 'foo:8080',
                   'verb': 'GET',
                   'path': '/bar',
                   'params': params}

        # Now validate the signature based on the dummy request
        self.assertTrue(self.controller.check_signature(self.creds_ref,
                                                        sig_ref))

    def test_signature_validate_no_signature(self):
        """Test signature validation when signature is not presented in signature
        reference data.
        """

        access = self.blob['access']
        params = {'SignatureMethod': 'HmacSHA256',
                  'SignatureVersion': '2',
                  'AWSAccessKeyId': access}

        sig_ref = {'access': access,
                   'signature': None,
                   'host': 'foo:8080',
                   'verb': 'GET',
                   'path': '/bar',
                   'params': params}

        creds_ref = {'user_id': self.user_id,
                     'tenant_id': self.project_id,
                     'access': self.blob['access'],
                     'secret': self.blob['secret'],
                     'trust_id': None
                     }

        # Now validate the signature based on the dummy request
        self.assertRaises(exception.Unauthorized,
                          self.controller.check_signature,
                          creds_ref, sig_ref)

    def test_signature_validate_invalid_signature(self):
        """Test signature validation when signature is not signed on
        the correct data.
        """
        access = self.blob['access']
        secret = self.blob['secret']
        signer = ec2_utils.Ec2Signer(secret)
        params = {'SignatureMethod': 'HmacSHA256',
                  'SignatureVersion': '2',
                  'AWSAccessKeyId': access}
        request = {'host': 'foo',
                   'verb': 'GET',
                   'path': '/bar',
                   'params': params}
        signature = signer.generate(request)

        sig_ref = {'access': access,
                   'signature': signature,
                   'host': 'foo:8080',
                   'verb': 'GET',
                   'path': '/bar',
                   'params': params}

        creds_ref = {'user_id': self.user_id,
                     'tenant_id': self.project_id,
                     'access': self.blob['access'],
                     'secret': self.blob['secret'],
                     'trust_id': None
                     }

        # Now validate the signature based on the dummy request
        self.assertRaises(exception.Unauthorized,
                          self.controller.check_signature,
                          creds_ref, sig_ref)
