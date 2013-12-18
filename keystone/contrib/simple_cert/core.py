# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

from oslo.config import cfg
import pecan
from pecan import rest

from keystone.common import wsgi

CONF = cfg.CONF


class Certificates(rest.RestController):

    @pecan.expose(content_type='application/x-pem-file')
    def get_all(self):
        with open(CONF.signing.certfile, 'r') as cert_file:
            data = cert_file.read()

        pecan.response.status_code = 200
        return data


class RootController(object):

    certificates = Certificates()

    @pecan.expose(content_type='application/x-pem-file')
    def ca(self):
        with open(CONF.signing.ca_certs, 'r') as ca_file:
            data = ca_file.read()

        pecan.response.status_code = 200
        return data


class SimpleCertExtension(wsgi.PecanExtensionRouter):

    controllers = {'/OS-SIMPLE-CERT/{path_info:.*}': RootController()}
