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

import os
import eventlet

from keystone import test
from keystone.common import wsgi

do_monkeypatch = not os.getenv('STANDARD_THREADS')
eventlet.patcher.monkey_patch(all=False, socket=True, time=True,
                              thread=do_monkeypatch)


class ServerTestCase(test.TestCase):

    def setUp(self):
        super(ServerTestCase, self).setUp()
        self.load_backends()
        self._servers = []

    def tearDown(self):
        """Kill running servers and release references to avoid leaks."""
        for server in self._servers:
            server.kill()

        self._servers = []

    def request(self, host='0.0.0.0', port=80, method='GET', path='/',
                headers=None, body=None, token=None, expected_status=None):
        """Perform request and fetch httplib.HTTPResponse from the server."""

        # Initialize headers dictionary
        headers = {} if not headers else headers

        if token:
            headers['X-Auth-Token'] = str(token)

        connection = self.HTTPConnection(host, port, timeout=100000)

        # Perform the request
        connection.request(method, path, body, headers)
        # Retrieve the response so we can close the connection
        response = connection.getresponse()

        response.body = response.read()
        response.status_code = response.status

        # Close the connection
        connection.close()

        # Automatically assert HTTP status code
        if expected_status:
            self.assertResponseStatus(response, expected_status)
        else:
            self.assertResponseSuccessful(response)
        self.assertValidResponseHeaders(response)

        # Contains the response headers, body, etc
        return response

    def _get_port(self, server):
        return server.socket_info['socket'][1]

    def serveapp(self, config, name=None, cert=None, key=None, ca=None,
                 cert_required=None, host="127.0.0.1", port=0):
        app = self.loadapp(config, name=name)
        server = wsgi.Server(app, host, port)
        if cert is not None and ca is not None and key is not None:
            server.set_ssl(certfile=cert, keyfile=key, ca_certs=ca,
                           cert_required=cert_required)
        server.start(key='socket')

        # Service catalog tests need to know the port we ran on.
        port = server.socket_info['socket'][1]
        self.opt(public_port=port, admin_port=port)
        self._servers.append(server)
        return server
