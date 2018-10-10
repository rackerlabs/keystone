# Copyright 2018 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import random
import webob

from keystone.tests import unit


class HealthCheckTestCase(unit.TestCase):
    def setUp(self):
        super(HealthCheckTestCase, self).setUp()
        self.load_backends()
        self.public_app = self.loadapp('public')
        self.public_port = random.randint(40000, 60000)

        self.config_fixture.config(
            public_endpoint='http://localhost:%d' % self.public_port)

    def _test_get_healthcheck(self, app_name):
        app = self.loadapp(app_name)
        req = webob.Request.blank('/healthcheck')
        req.method = 'GET'
        resp = req.get_response(app)
        self.assertEqual(200, resp.status_int)

    def test_public(self):
        self._test_get_healthcheck('public')

    def test_admin(self):
        self._test_get_healthcheck('admin')
