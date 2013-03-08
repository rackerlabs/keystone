# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack LLC
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

from keystone import config
from keystone import controllers
from keystone.openstack.common import jsonutils
from keystone import test


CONF = config.CONF

class VersionTestCase(test.TestCase):
    def setUp(self):
        super(VersionTestCase, self).setUp()
        self.load_backends()
        self.public_app = self.loadapp('keystone', 'main')
        self.public_server = self.serveapp('keystone', name='main')

    def test_public_version_v3_html(self):
        print CONF.public_port
        client = self.client(self.public_app)
        headers = {'Accept': 'text/html'}
        resp = client.get('/v3/',headers)
        self.assertEqual(resp.status_int, 200)
        self.assertTrue( 'text/html' in  resp.headers.get('Content-Type'))
        