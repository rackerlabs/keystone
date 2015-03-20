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

import pecan

from keystone.api.common import controller
from keystone.api import v2
from keystone.api import v3
from keystone.common import json_home


__all__ = ['AdminRootController',
           'PublicRootController',
           'RootController']


class RootController(object):

    available_versions = set()

    @classmethod
    def register_version(cls, version):
        cls.available_versions.add(version)

    @classmethod
    def clear_versions(cls):
        cls.available_versions.clear()

    @controller.expose
    @pecan.expose('keystone:%s' % controller.JSON_HOME, controller.JSON_HOME)
    def index(self):
        accept = pecan.request.accept.best_match([controller.JSON,
                                                  controller.JSON_HOME])

        if accept == controller.JSON_HOME:
            pecan.response.content_type = controller.JSON_HOME
            resources = {}

            if 'v3' in self.available_versions:
                # FIXME(jamielennox): This is horrible, however the only way to
                # do json home listing with the current extension model. Fix
                # this as controllers and extensions are moved over to pecan.
                data = v3.RootController().get_json_home_data(extensions=True)
                json_home.translate_urls(data, '/v3')
                resources = data['resources']

            return {'resources': resources}

        else:
            versions = []
            pecan.response.status = 300

            if 'v3' in self.available_versions:
                versions.append(v3.RootController.data(self.endpoint_type))

            if 'v2.0' in self.available_versions:
                versions.append(v2.RootController.data(self.endpoint_type))

            pecan.override_template('keystone:application/json',
                                    content_type='application/json')

            return {'versions': {'values': versions}}


class PublicRootController(RootController):
    endpoint_type = 'public'


class AdminRootController(RootController):
    endpoint_type = 'admin'
