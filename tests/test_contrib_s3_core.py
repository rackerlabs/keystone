# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
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

import copy
import uuid

from keystone.contrib.s3.core import S3Controller
from keystone.contrib import ec2

from keystone import exception
from keystone import test

from keystone.common import utils


class S3ContribCore(test.TestCase):
    def setUp(self):
        super(S3ContribCore, self).setUp()

        self.load_backends()

        self.ec2_api = ec2.Manager()
        self.controller = S3Controller()

    def test_good_signature(self):
        creds_ref = {'secret':
                     'b121dd41cdcc42fe9f70e572e84295aa'}
        credentials = {'token':
                       'UFVUCjFCMk0yWThBc2dUcGdBbVk3UGhDZmc9PQphcHB'
                       'saWNhdGlvbi9vY3RldC1zdHJlYW0KVHVlLCAxMSBEZWMgMjAxM'
                       'iAyMTo0MTo0MSBHTVQKL2NvbnRfczMvdXBsb2FkZWRfZnJ'
                       'vbV9zMy50eHQ=',
                       'signature': 'IL4QLcLVaYgylF9iHj6Wb8BGZsw='}

        self.assertIsNone(self.controller.check_signature(creds_ref,
                                                          credentials))

    def test_bad_signature(self):
        creds_ref = {'secret':
                     'b121dd41cdcc42fe9f70e572e84295aa'}
        credentials = {'token':
                       'UFVUCjFCMk0yWThBc2dUcGdBbVk3UGhDZmc9PQphcHB'
                       'saWNhdGlvbi9vY3RldC1zdHJlYW0KVHVlLCAxMSBEZWMgMjAxM'
                       'iAyMTo0MTo0MSBHTVQKL2NvbnRfczMvdXBsb2FkZWRfZnJ'
                       'vbV9zMy50eHQ=',
                       'signature': uuid.uuid4().hex}

        self.assertRaises(exception.Unauthorized,
                          self.controller.check_signature,
                          creds_ref, credentials)

    def test_portless_signature(self):
        creds_ref = {'access': '1be42673c6c94dc49135d64627a595c1',
                     'tenant_id': 'ec49e71e5f8148b1a2cc08f53fc2e0c9',
                     'secret': 'a1534244b64d444b9a4afafa127d7a7e',
                     'user_id': 'a19b2573025c40b2be0b34d044abe808'}
        credentials = {'path': '/',
                       'server_string': 'whaterver',
                       'verb': 'GET',
                       'params': {'SignatureVersion': '2',
                                  'SignatureMethod': 'HmacSHA256'},
                       'host': '127.0.0.1:5000'}
        credentials_without_port = copy.deepcopy()
        credentials_without_port['host'] = '127.0.0.1'

        # signer must be generated every time you generate a signature
        signer = utils.Ec2Signer(creds_ref['secret'])
        self.assertNotEqual(signer.generate(credentials),
                            signer.generate(credentials))
        a = utils.Ec2Signer(creds_ref['secret'])
        b = utils.Ec2Signer(creds_ref['secret'])
        self.assertEqual(a.generate(credentials),
                         b.generate(credentials))

        # simulating library chopping off the port
        signer = utils.Ec2Signer(creds_ref['secret'])
        signature = signer.generate(credentials_without_port)
        credentials['signature'] = signature
        self.assertIsNone(self.controller.check_signature(creds_ref,
                                                          credentials))
