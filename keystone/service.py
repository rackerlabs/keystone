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
from keystone.common import logging
from keystone.common import wsgi
from keystone import exception
from keystone import extensions
from keystone import policy
from keystone.routers import crud, identity, policy, catalog
from keystone.routers import token

LOG = logging.getLogger(__name__)


"""
only ComposingRouters in this file.  The routers for the submodules should be
in the module specific router files
"""


class AdminRouter(wsgi.ComposingRouter):
    def __init__(self):
        mapper = routes.Mapper()
        identity_router = identity.Admin()
        token_router = token.TokenRouter()
        version_router = catalog.VersionRouter('admin')
        extension_router = extensions.ExtensionRouter()
        routers = [identity_router, token_router, version_router,
                   extension_router]
        super(AdminRouter, self).__init__(mapper, routers)


class PublicRouter(wsgi.ComposingRouter):
    def __init__(self):
        mapper = routes.Mapper()

        identity_router = identity.Public()
        token_router = token.TokenRouter()
        version_router = catalog.VersionRouter('public')
        extension_router = extensions.ExtensionRouter(False)

        routers = [identity_router, token_router, version_router,
                   extension_router]

        super(PublicRouter, self).__init__(mapper, routers)


class PublicVersionRouter(wsgi.ComposingRouter):
    def __init__(self):
        mapper = routes.Mapper()
        routers = [catalog.VersionsRouter('public')]
        super(PublicVersionRouter, self).__init__(mapper, routers)


class AdminVersionRouter(wsgi.ComposingRouter):
    def __init__(self):
        mapper = routes.Mapper()
        routers = [catalog.VersionsRouter('admin')]
        super(AdminVersionRouter, self).__init__(mapper, routers)


class V3Router(wsgi.ComposingRouter):

    def __init__(self):
        mapper = routes.Mapper()
        routers = []
        catalog.V3_routers(mapper, routers)
        identity.V3_routers(mapper, routers)
        policy.V3_routers(mapper, routers)
        #TODO put token routes here
        super(V3Router, self).__init__(mapper, routers)


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
    return V3Router()
