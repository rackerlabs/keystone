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

import uuid
import routes
import json

from keystone import config
from keystone import catalog
from keystone.common import cms
from keystone.common import logging
from keystone.common import wsgi
from keystone import exception
from keystone import identity
from keystone.openstack.common import timeutils
from keystone import policy
from keystone.token import routers as token
from keystone import v3service

LOG = logging.getLogger(__name__)


class AdminRouter(wsgi.ComposingRouter):
    def __init__(self):
        mapper = routes.Mapper()

        version_controller = VersionController('admin')
        mapper.connect('/',
                       controller=version_controller,
                       action='get_version')

        # Miscellaneous Operations
        extensions_controller = AdminExtensionsController()
        mapper.connect('/extensions',
                       controller=extensions_controller,
                       action='get_extensions_info',
                       conditions=dict(method=['GET']))
        mapper.connect('/extensions/{extension_alias}',
                       controller=extensions_controller,
                       action='get_extension_info',
                       conditions=dict(method=['GET']))
        identity_router = identity.routers.Admin()
        token_router = token.TokenRouter()
        routers = [identity_router, token_router]
        super(AdminRouter, self).__init__(mapper, routers)


class PublicRouter(wsgi.ComposingRouter):
    def __init__(self):
        mapper = routes.Mapper()

        version_controller = VersionController('public')
        mapper.connect('/',
                       controller=version_controller,
                       action='get_version')
        # Miscellaneous
        extensions_controller = PublicExtensionsController()
        mapper.connect('/extensions',
                       controller=extensions_controller,
                       action='get_extensions_info',
                       conditions=dict(method=['GET']))
        mapper.connect('/extensions/{extension_alias}',
                       controller=extensions_controller,
                       action='get_extension_info',
                       conditions=dict(method=['GET']))

        identity_router = identity.routers.Public()
        token_router = token.TokenRouter()
        routers = [identity_router, token_router]

        super(PublicRouter, self).__init__(mapper, routers)


class PublicVersionRouter(wsgi.ComposingRouter):
    def __init__(self):
        mapper = routes.Mapper()
        version_controller = VersionController('public')
        mapper.connect('/',
                       controller=version_controller,
                       action='get_versions')
        routers = []
        super(PublicVersionRouter, self).__init__(mapper, routers)


class AdminVersionRouter(wsgi.ComposingRouter):
    def __init__(self):
        mapper = routes.Mapper()
        version_controller = VersionController('admin')
        mapper.connect('/',
                       controller=version_controller,
                       action='get_versions')
        routers = []
        super(AdminVersionRouter, self).__init__(mapper, routers)


class VersionController(wsgi.Application):
    def __init__(self, version_type):
        self.catalog_api = catalog.Manager()
        self.url_key = '%sURL' % version_type

        super(VersionController, self).__init__()

    def _get_identity_url(self, context):
        catalog_ref = self.catalog_api.get_catalog(context=context,
                                                   user_id=None,
                                                   tenant_id=None)
        for region, region_ref in catalog_ref.iteritems():
            for service, service_ref in region_ref.iteritems():
                if service == 'identity':
                    return service_ref[self.url_key]

        raise exception.NotImplemented()

    def _get_versions_list(self, context):
        """The list of versions is dependent on the context."""
        identity_url = self._get_identity_url(context)
        if not identity_url.endswith('/'):
            identity_url = identity_url + '/'

        versions = {}
        versions['v2.0'] = {
            'id': 'v2.0',
            'status': 'beta',
            'updated': '2011-11-19T00:00:00Z',
            'links': [
                {
                    'rel': 'self',
                    'href': identity_url,
                }, {
                    'rel': 'describedby',
                    'type': 'text/html',
                    'href': 'http://docs.openstack.org/api/openstack-'
                            'identity-service/2.0/content/'
                }, {
                    'rel': 'describedby',
                    'type': 'application/pdf',
                    'href': 'http://docs.openstack.org/api/openstack-'
                            'identity-service/2.0/identity-dev-guide-'
                            '2.0.pdf'
                }
            ],
            'media-types': [
                {
                    'base': 'application/json',
                    'type': 'application/vnd.openstack.identity-v2.0'
                            '+json'
                }, {
                    'base': 'application/xml',
                    'type': 'application/vnd.openstack.identity-v2.0'
                            '+xml'
                }
            ]
        }

        return versions

    def get_versions(self, context):
        versions = self._get_versions_list(context)
        return wsgi.render_response(status=(300, 'Multiple Choices'), body={
            'versions': {
                'values': versions.values()
            }
        })

    def get_version(self, context):
        versions = self._get_versions_list(context)
        return wsgi.render_response(body={
            'version': versions['v2.0']
        })


class NoopController(wsgi.Application):
    def __init__(self):
        super(NoopController, self).__init__()

    def noop(self, context):
        return {}


class ExtensionsController(wsgi.Application):
    """Base extensions controller to be extended by public and admin API's."""

    def __init__(self, extensions=None):
        super(ExtensionsController, self).__init__()

        self.extensions = extensions or {}

    def get_extensions_info(self, context):
        return {'extensions': {'values': self.extensions.values()}}

    def get_extension_info(self, context, extension_alias):
        try:
            return {'extension': self.extensions[extension_alias]}
        except KeyError:
            raise exception.NotFound(target=extension_alias)


class PublicExtensionsController(ExtensionsController):
    pass


class AdminExtensionsController(ExtensionsController):
    def __init__(self, *args, **kwargs):
        super(AdminExtensionsController, self).__init__(*args, **kwargs)

        # TODO(dolph): Extensions should obviously provide this information
        #               themselves, but hardcoding it here allows us to match
        #               the API spec in the short term with minimal complexity.
        self.extensions['OS-KSADM'] = {
            'name': 'Openstack Keystone Admin',
            'namespace': 'http://docs.openstack.org/identity/api/ext/'
                         'OS-KSADM/v1.0',
            'alias': 'OS-KSADM',
            'updated': '2011-08-19T13:25:27-06:00',
            'description': 'Openstack extensions to Keystone v2.0 API '
                           'enabling Admin Operations.',
            'links': [
                {
                    'rel': 'describedby',
                    # TODO(dolph): link needs to be revised after
                    #              bug 928059 merges
                    'type': 'text/html',
                    'href': 'https://github.com/openstack/identity-api',
                }
            ]
        }


@logging.fail_gracefully
def public_app_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)
    return PublicRouter()


@logging.fail_gracefully
def admin_app_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)
    return AdminRouter()


@logging.fail_gracefully
def public_version_app_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)
    return PublicVersionRouter()


@logging.fail_gracefully
def admin_version_app_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)
    return AdminVersionRouter()


@logging.fail_gracefully
def v3_app_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)
    return v3service.V3Router()
