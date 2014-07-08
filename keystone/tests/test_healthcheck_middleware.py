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

import mock
import webob

from keystone.middleware import healthcheck
from keystone import tests


class FakeApp(object):
    def __call__(self, env, start_response):
        req = webob.Request(env)
        return webob.Response(request=req, body='FAKE APP')(
            env, start_response)


class HealthcheckMiddlewareTest(tests.TestCase):
    @mock.patch('keystone.common.sql.get_session')
    def setUp(self, mock_get_session):
        self._middleware = healthcheck.HealthCheckMiddleware(FakeApp())
        self._response_status = None
        super(HealthcheckMiddlewareTest, self).setUp()

    def _start_fake_response(self, status, headers):
        self._response_status = int(status.split(' ', 1)[0])

    @mock.patch('keystone.middleware.healthcheck.HealthCheckMiddleware._check_db')  # noqa
    def test_healthcheck(self, mock_check_db):
        mock_check_db.return_value = True
        req = webob.Request.blank('/healthcheck',
                                  environ={'REQUEST_METHOD': 'GET'})
        resp = self._middleware(req.environ, self._start_fake_response)
        self.assertEqual(200, self._response_status)
        self.assertEqual(['OK'], resp)

    def test_healthcheck_skipped(self):
        req = webob.Request.blank('/', environ={'REQUEST_METHOD': 'GET'})
        resp = self._middleware(req.environ, self._start_fake_response)
        self.assertEqual(200, self._response_status)
        self.assertEqual(['FAKE APP'], resp)

    @mock.patch('os.path.exists')
    def test_healthcheck_disabled(self, mock_exists):
        mock_exists.return_value = True
        req = webob.Request.blank('/healthcheck',
                                  environ={'REQUEST_METHOD': 'GET'})
        resp = self._middleware(req.environ, self._start_fake_response)
        self.assertEqual(503, self._response_status)
        self.assertEqual(['DISABLED BY FILE'], resp)

    @mock.patch('keystone.middleware.healthcheck.HealthCheckMiddleware._check_db')  # noqa
    def test_db_failed(self, mock_check_db):
        mock_check_db.return_value = False
        req = webob.Request.blank('/healthcheck',
                                  environ={'REQUEST_METHOD': 'GET'})
        resp = self._middleware(req.environ, self._start_fake_response)
        self.assertEqual(503, self._response_status)
        self.assertEqual(['DATABASE FAILED'], resp)
