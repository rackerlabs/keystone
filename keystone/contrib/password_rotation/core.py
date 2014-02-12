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

from keystone.common import extension
from keystone.contrib.password_rotation import routers


class Extension(object):
    alias = 'OS-PW-ROTATE'
    metadata = {
        'name': 'OpenStack Password Rotation API',
        'namespace': 'http://docs.openstack.org/identity/api/ext/'
                     'OS-PW-ROTATE/v1.0',
        'alias': alias,
        'updated': '2014-04-22T00:00:0-00:00',
        'description': 'OpenStack API for rotating passwords.',
        'links': [
            {
                'rel': 'describedby',
                'type': 'text/html',
                'href': ('https://github.com/openstack/identity-api/blob/master/'
                         'openstack-identity-api/v3/src/markdown/'
                         'identity-api-v3-os-pw-rotate-ext.md'),
            }
        ]
    }

    @staticmethod
    def register():
        extension.register_admin_extension(
            Extension.alias, Extension.metadata)
        extension.register_public_extension(
            Extension.alias, Extension.metadata)


def extension_factory(global_config, **local_config):
    def factory(app):
        Extension.register()
        return routers.ExtensionRouter(app)
    return factory
