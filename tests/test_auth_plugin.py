# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack LLC
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

from keystone.common import logging
from keystone import auth
from keystone import config
from keystone import exception
from keystone import test


METHOD_NAME = 'simple-challenge-response'


class SimpleChallengeResponse(auth.AuthMethodHandler):
    def authenticate(self, context, auth_info, user_context):
        return {"challenge": "What's the name of your high school?"}


class TestAuthPlugin(test.TestCase):
    def setUp(self):
        super(TestAuthPlugin, self).setUp()
        self.config([
            test.etcdir('keystone.conf.sample'),
            test.testsdir('test_overrides.conf'),
            test.testsdir('backend_sql.conf'),
            test.testsdir('backend_sql_disk.conf'),
            test.testsdir('test_auth_plugin.conf')])
        self.load_backends()
        auth.controllers.AUTH_METHODS[METHOD_NAME] = SimpleChallengeResponse()
        self.api = auth.controllers.Auth()

    def test_unsupported_auth_method(self):
        auth_json = {'methods': ['abc']}
        auth_json['abc'] = {'test': 'test'}
        auth_json = {'authentication': auth_json}
        self.assertRaises(exception.AuthMethodNotSupported,
                          auth.controllers.AuthInfo,
                          None,
                          auth_json)

    def test_addition_auth_steps(self):
        auth_json = {'methods': ['simple-challenge-response']}
        auth_json['simple-challenge-response'] = {
            'test': 'test'}
        auth_json = {'authentication': auth_json}
        auth_info = auth.controllers.AuthInfo(None, auth_json)
        auth_context = {'extras': {}, 'method_names': []}
        try:
            self.api.authenticate({}, auth_info, auth_context)
        except exception.AdditionalAuthRequired as e:
            self.assertTrue('methods' in e.authentication)
            self.assertTrue(METHOD_NAME in e.authentication['methods'])
            self.assertTrue(METHOD_NAME in e.authentication)
