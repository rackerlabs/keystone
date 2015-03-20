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

import abc

from oslo_config import cfg
import pecan
import pecan.rest
import six

from keystone.api.common import controller
from keystone import assignment
from keystone.common import extension
from keystone import exception
from keystone import identity
from keystone import resource
from keystone import token

CONF = cfg.CONF


__all__ = ['AdminRootController',
           'PublicRootController',
           'RootController']


class ExtensionController(pecan.rest.RestController):
    """Base extensions controller to be extended by public and admin API's."""

    def __init__(self, data):
        super(ExtensionController, self).__init__()
        self.extension_data = data

    @controller.expose
    def get_all(self):
        return {'extensions': {'values': self.extension_data.values()}}

    @controller.expose
    def get_one(self, extension_alias):
        try:
            return {'extension': self.extension_data[extension_alias]}
        except KeyError:
            raise exception.NotFound(target=extension_alias)


@six.add_metaclass(abc.ABCMeta)
class RootController(controller.PecanRoutesController):

    @classmethod
    def data(cls, endpoint_type='public'):
        return {
            'id': 'v2.0',
            'status': 'stable',
            'updated': '2014-04-17T00:00:00Z',
            'links': [
                {
                    'rel': 'self',
                    'href': cls.get_identity_url(endpoint_type, 'v2.0'),
                }, {
                    'rel': 'describedby',
                    'type': 'text/html',
                    'href': 'http://docs.openstack.org/',
                }
            ],
            'media-types': [
                {
                    'base': 'application/json',
                    'type': controller.MEDIA_TYPE_JSON % 'v2.0'
                }
            ]
        }

    @controller.expose
    def index(self):
        return {'version': self.data()}


class PublicRootController(RootController):

    extensions = ExtensionController(extension.PUBLIC_EXTENSIONS)

    @classmethod
    def data(cls):
        return super(PublicRootController, cls).data('public')

    def get_routers(self, mapper):
        return [
            assignment.routers.Public(),
            token.routers.Router(),
        ]


class AdminRootController(RootController):

    extensions = ExtensionController(extension.ADMIN_EXTENSIONS)

    @classmethod
    def data(cls):
        return super(AdminRootController, cls).data('admin')

    def get_routers(self, mapper):
        return [
            identity.routers.Admin(),
            assignment.routers.Admin(),
            token.routers.Router(),
            resource.routers.Admin(),
        ]
