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
import webob

from keystone import config
from keystone import service
from keystone import test


CONF = config.CONF


class TokenControllerTest(test.TestCase):
    def setUp(self):
        super(TokenControllerTest, self).setUp()
        self.api = service.AdminRouter()

    def _test_authentication(self, body, content_type='application/json'):
        req = webob.Request.blank("/tokens", content_type=content_type,
                                  method='POST', body=body)
        res = req.get_response(self.api)
        return res

    def test_authenticate_blank_request_body(self):
        """Verify sending empty json dict raises the right exception."""
        res = self._test_authentication(json.dumps(dict()))
        self.assertEquals(res.status_int, webob.exc.HTTPBadRequest.code)
        self.assertTrue('auth' in res.body, res.body)

    def test_authenticate_blank_auth(self):
        """Verify sending blank 'auth' raises the right exception."""
        res = self._test_authentication(json.dumps(dict(auth=None)))
        self.assertEquals(res.status_int, webob.exc.HTTPBadRequest.code)
        self.assertTrue('auth' in res.body, res.body)

    def test_authenticate_invalid_auth_content(self):
        """Verify sending invalid 'auth' raises the right exception."""
        res = self._test_authentication(json.dumps(dict(auth='abcd')))
        self.assertEquals(res.status_int, webob.exc.HTTPBadRequest.code)
        self.assertTrue('auth' in res.body, res.body)
