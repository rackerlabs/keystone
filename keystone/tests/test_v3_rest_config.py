# Copyright 2014 IBM Corp.
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

from keystone.tests import test_v3


class RestConfigTests(test_v3.RestfulTestCase):
    EXTENSION_NAME = 'rest_config'
    EXTENSION_TO_ADD = 'rest_config_extension'

    def test_get_config(self):
        resp = self.get('/OS-REST-CONFIG/config')
        self.assertIn('config', resp.result)
        self.assertIn('identity', resp.result['config'])
        self.assertIn('default_domain_id', resp.result['config']['identity'])
        self.assertIn('ldap', resp.result['config'])
        self.assertIn('admin_port', resp.result['config'])

    def test_get_config_by_group(self):
        resp = self.get('/OS-REST-CONFIG/config?group=identity')
        self.assertIn('config', resp.result)
        self.assertIn('identity', resp.result['config'])
        self.assertNotIn('ldap', resp.result['config'])
        self.assertNotIn('admin_port', resp.result['config'])
