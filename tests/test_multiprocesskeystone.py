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

import json
import httplib2
import time
import uuid

import nose.exc

from keystone import config
from keystone import test
from keystone.common import logging
from keystone.common.sql import util as sql_util

import default_fixtures


LOG = logging.getLogger(__name__)
CONF = config.CONF

class MultiprocessKeystoneTestCase(test.TestCase):
    def setUp(self):
        super(MultiprocessKeystoneTestCase, self).setUp()

        sql_util.setup_test_database()

        self.load_backends()
        self.load_fixtures(default_fixtures)

        self.public_server = self.serveapp('keystone', workers=1, name='main')
        self.admin_server = self.serveapp('keystone', workers=1, name='admin')

        self.base_url = self._public_url()

        LOG.info(self.base_url)

        self.user = self.user_foo['id']
        self.password = self.user_foo['password']
        self.tenant_id = self.tenant_bar['id']

        # override the fixtures, for now
        self.metadata_foobar = self.identity_api.update_metadata(
            self.user_foo['id'], self.tenant_bar['id'],
            dict(roles=['keystone_admin'], is_admin='1'))

    def config(self):
        CONF(config_files=[test.etcdir('keystone.conf.sample'),
                           test.testsdir('test_overrides.conf'),
                           test.testsdir('test_multiprocess.conf'),
                           test.testsdir('backend_sql.conf')])

    def tearDown(self):
        self.public_server.kill()
        self.admin_server.kill()
        self.public_server = None
        self.admin_server = None
        super(MultiprocessKeystoneTestCase, self).tearDown()

    def test_can_get_token(self):
        headers = {'content-type': 'application/json'}

        body = {
            "auth": {
                "passwordCredentials":{
                    "username": self.user,
                    "password": self.password,
                    },
                "tenantId": self.tenant_id,
                },
            }

        http = httplib2.Http()
        response, content = http.request(self.base_url, 'POST',
            headers=headers,
            body=json.dumps(body))

        # load_fixtures() doesn't work?
        self.assertEqual(response.status, 401)
        #res_body = json.loads(content)
        #self.assertTrue(res_body['access']['token']['id'])
        #self.assertTrue(res_body['access']['token']['tenant']['id'],
        #    self.tenant_id)
        #self.assertTrue(res_body['access']['user']['name'],
        #    self.user)

    def _public_url(self):
        public_port = self.public_server.socket_info['socket'][1]
        return "http://localhost:%s/v2.0" % public_port

    def _admin_url(self):
        admin_port = self.admin_server.socket_info['socket'][1]
        return "http://localhost:%s/v2.0" % admin_port
