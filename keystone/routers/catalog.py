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

from keystone.catalog import controllers
from keystone.routers import crud
from keystone.common import wsgi


class VersionRouter(wsgi.ComposableRouter):
    def __init__(self, description):
        self.description = description

    def add_routes(self, mapper):
        version_controller = controllers.VersionController(self.description)
        mapper.connect('/',
                       controller=version_controller,
                       action='get_version')


class VersionsRouter(wsgi.ComposableRouter):
    def __init__(self, description):
        self.description = description

    def add_routes(self, mapper):
        version_controller = controllers.VersionController(self.description)
        mapper.connect('/',
                       controller=version_controller,
                       action='get_versions')


def V3_routers(mapper, routers):
    routers.append(crud.Router(controllers.ServiceV3(),
                               'services', 'service'))
    routers.append(crud.Router(controllers.EndpointV3(),
                               'endpoints', 'endpoint'))
