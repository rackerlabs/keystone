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

from keystone.common import config
from keystone.common import wsgi
from keystone.contrib.simple_cert import controllers
from keystone.contrib.simple_cert import core


CONF = config.CONF


class SimpleCertExtension(wsgi.V3ExtensionRouter):

    PREFIX = 'OS-SIMPLE-CERT'

    def add_routes(self, mapper):
        controller = controllers.SimpleCert()

        mapper.connect('/%s/ca' % self.PREFIX,
                       controller=controller,
                       action='get_ca_certificate',
                       conditions=dict(method=['GET']))

        mapper.connect('/%s/certificates' % self.PREFIX,
                       controller=controller,
                       action='list_certificates',
                       conditions=dict(method=['GET']))

    def _get_version_data(self, request):
        url = CONF.public_endpoint
        if url:
            url = (url % CONF).rstrip('/') + '/v3'
        else:
            url = request.path_url.rstrip('/')

        return {
            'rel': 'http://docs.openstack.org/identity/rel/v3/extension',
            'href': '%s/%s/' % (url, self.PREFIX),
            'alias': core.EXTENSION_DATA['alias'],
            'description': core.EXTENSION_DATA['description'],
            'version': '1.0',
            'updated': core.EXTENSION_DATA['updated'],
        }
