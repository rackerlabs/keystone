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

import routes
from keystone.common import logging
from keystone.common import wsgi
from keystone import exception
from keystone import extensions
from keystone import policy
from keystone import catalog
from keystone import identity
from keystone import policy
from keystone import token

LOG = logging.getLogger(__name__)


"""
The only types of routers in this file should be ComposingRouters.
The routers for the submodules should be in the module specific router files
for example, the Composable Router for identity belongs in
keystone/identity/routers.py
"""


def _apis():
    return dict(catalog_api=catalog.Manager(),
                identity_api=identity.Manager(),
                policy_api=policy.Manager(),
                token_api=token.Manager())


class AdminRouter(wsgi.ComposingRouter):
    def __init__(self):
        mapper = routes.Mapper()
        routers = [identity.routers.Admin(_apis()),
                   token.routers.TokenRouter(_apis()),
                   catalog.routers.VersionRouter('admin'),
                   extensions.ExtensionRouter()]
        super(AdminRouter, self).__init__(mapper, routers)


class PublicRouter(wsgi.ComposingRouter):
    def __init__(self):
        mapper = routes.Mapper()

        routers = [identity.routers.Public(_apis()),
                   token.routers.TokenRouter(_apis()),
                   catalog.routers.VersionRouter('public'),
                   extensions.ExtensionRouter(False)]
        super(PublicRouter, self).__init__(mapper, routers)


class PublicVersionRouter(wsgi.ComposingRouter):
    def __init__(self):
        mapper = routes.Mapper()
        routers = [catalog.routers.VersionsRouter('public')]
        super(PublicVersionRouter, self).__init__(mapper, routers)


class AdminVersionRouter(wsgi.ComposingRouter):
    def __init__(self):
        mapper = routes.Mapper()
        routers = [catalog.routers.VersionsRouter('admin')]
        super(AdminVersionRouter, self).__init__(mapper, routers)


class V3Router(wsgi.ComposingRouter):

    def __init__(self):
        mapper = routes.Mapper()
        routers = []
        catalog.routers.V3_routers(mapper, routers, _apis())
        identity.routers.V3_routers(mapper, routers, _apis())
        policy.routers.V3_routers(mapper, routers, _apis())
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
