# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

import routes

from keystone.common import config
from keystone import tests
from keystone.token import routers


CONF = config.CONF


class UUIDTokenRouterTestCase(tests.TestCase):

    def test_token_router(self):
        mapper = routes.Mapper()
        routers.Router(mapper)
        self.assertEqual('authenticate',
                         mapper.match('/tokens')['action'])
        self.assertIsNone(mapper.match('/certificates/ca'))


class PKITokenRouterTestCase(tests.TestCase):
    def config(self, config_files):
        config_files.append('test_pki_token_provider.conf')
        super(PKITokenRouterTestCase, self).config(config_files)

    def test_pki_router(self):
        mapper = routes.Mapper()
        routers.Router(mapper)
        self.assertTrue(mapper.match('/tokens'))
        self.assertEqual('ca_cert',
                         mapper.match('/certificates/ca')['action'])
