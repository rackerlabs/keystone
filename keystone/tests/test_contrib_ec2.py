# Copyright 2012 OpenStack Foundation
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
from keystone import tests


class Ec2ControllerTest(tests.TestCase):
    def setUp(self):
        super(Ec2ControllerTest, self).setUp()

        self.load_backends()

        self.controller = controllers.Ec2Controller()

    def test_check_signature_ok(self):
        creds_ref = {'access': uuid.uuid4().hex,
                     'secret': uuid.uuid4().hex}
        params = {'SignatureMethod': 'HmacSHA256',
                  'SignatureVersion': '2',
                  'AWSAccessKeyId': creds_ref['access']}
        creds_sign = {'host': "http://keystone:5000",
                      'verb': 'GET',
                      'path': '/bar',
                      'params': params}

        signer = ec2_utils.Ec2Signer(creds_ref['secret'])
        signature = signer.generate(creds_sign)

        creds = dict(creds_sign)
        creds['signature'] = signature

        self.assertIsNone(self.controller.check_signature(creds_ref,
                                                          creds))

    def test_check_signature_no_port_ok(self):
        creds_ref = {'access': uuid.uuid4().hex,
                     'secret': uuid.uuid4().hex}
        params = {'SignatureMethod': 'HmacSHA256',
                  'SignatureVersion': '2',
                  'AWSAccessKeyId': creds_ref['access']}
        creds_sign = {'host': "http://keystone",
                      'verb': 'GET',
                      'path': '/bar',
                      'params': params}

        signer = ec2_utils.Ec2Signer(creds_ref['secret'])
        signature = signer.generate(creds_sign)

        creds = dict(creds_sign)
        creds['hosts'] = "http://keystone:5000"
        creds['signature'] = signature

        self.assertIsNone(self.controller.check_signature(creds_ref,
                                                          creds))

    def test_check_signature_fail(self):
        creds_ref = {'access': uuid.uuid4().hex,
                     'secret': uuid.uuid4().hex}
        params = {'SignatureMethod': 'HmacSHA256',
                  'SignatureVersion': '2',
                  'AWSAccessKeyId': creds_ref['access']}
        creds_sign = {'host': "http://keystone",
                      'verb': 'GET',
                      'path': '/bar',
                      'params': params}

        signature = 'wrong_signature'

        creds = dict(creds_sign)
        creds['hosts'] = "http://keystone:5000"
        creds['signature'] = signature

        self.assertRaises(exception.Unauthorized,
                          self.controller.check_signature,
                          creds_ref, creds)
