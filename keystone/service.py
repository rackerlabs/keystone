# Copyright 2012 OpenStack Foundation
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

import functools
import sys

import routes

from keystone import assignment
from keystone import auth
from keystone import catalog
from keystone.common import wsgi
from keystone import config
from keystone import controllers
from keystone import credential
from keystone import identity
from keystone.openstack.common import log
from keystone import policy
from keystone import routers
from keystone import token
from keystone import trust


CONF = config.CONF
LOG = log.getLogger(__name__)

v2_admin_version_router = None
v2_public_version_router = None
public_version_router = None
admin_version_router = None
v3_admin_version_router = None
v3_public_version_router = None
v3_router = None


def fail_gracefully(f):
    """Logs exceptions and aborts."""
    @functools.wraps(f)
    def wrapper(*args, **kw):
        try:
            return f(*args, **kw)
        except Exception as e:
            LOG.debug(e, exc_info=True)

            # exception message is printed to all logs
            LOG.critical(e)
            sys.exit(1)

    return wrapper


@fail_gracefully
def public_app_factory(global_conf, **local_conf):
    global v2_public_version_router
    controllers.register_version('v2.0')
    v2_public_version_router = routers.VersionV2('public')
    return wsgi.ComposingRouter(routes.Mapper(),
                                [assignment.routers.Public(),
                                 token.routers.Router(),
                                 v2_public_version_router,
                                 routers.Extension(False)])


@fail_gracefully
def admin_app_factory(global_conf, **local_conf):
    global v2_admin_version_router
    v2_admin_version_router = routers.VersionV2('admin')
    return wsgi.ComposingRouter(routes.Mapper(),
                                [identity.routers.Admin(),
                                 assignment.routers.Admin(),
                                 token.routers.Router(),
                                 v2_admin_version_router,
                                 routers.Extension()])


@fail_gracefully
def public_version_app_factory(global_conf, **local_conf):
    global public_version_router
    public_version_router = routers.Versions('public')
    return wsgi.ComposingRouter(routes.Mapper(), [public_version_router])


@fail_gracefully
def admin_version_app_factory(global_conf, **local_conf):
    global admin_version_router
    admin_version_router = routers.Versions('admin')
    return wsgi.ComposingRouter(routes.Mapper(), [admin_version_router])


@fail_gracefully
def v3_app_factory(global_conf, **local_conf):
    global v3_admin_version_router
    global v3_public_version_router
    global v3_router

    controllers.register_version('v3')
    mapper = routes.Mapper()
    sub_routers = []
    _routers = []

    router_modules = [assignment, auth, catalog, credential, identity, policy]
    if CONF.trust.enabled:
        router_modules.append(trust)

    for module in router_modules:
        routers_instance = module.routers.Routers()
        _routers.append(routers_instance)
        routers_instance.append_v3_routers(mapper, sub_routers)

    # Add in the v3 version api
    v3_admin_version_router = routers.VersionV3('admin', _routers)
    sub_routers.append(v3_admin_version_router)
    v3_public_version_router = routers.VersionV3('public', _routers)
    sub_routers.append(v3_public_version_router)
    # TODO(ayoung): put token routes here

    v3_router = wsgi.ComposingRouter(mapper, sub_routers)
    return v3_router
