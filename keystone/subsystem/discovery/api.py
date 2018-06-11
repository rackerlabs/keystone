#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from keystone.server.flask import common as flask_common
from keystone.subsystem.discovery import controllers

class DiscoveryRootResource(flask_common.Resource):
    _controller_cls = controllers.DiscoveryController

    def get(self):
        return self._controller.get_versions()



class DiscoveryV3Resource(flask_common.Resource):
    pass


class DiscoveryRootAPI(flask_common.APIBase):
    _import_name = __name__

    resource_mapping = [
        flask_common.ResourceMap(resource=DiscoveryRootResource, urls=['/'],
                                 kwargs={}),
        flask_common.ResourceMap(resource=DiscoveryV3Resource, urls=['/v3'],
                                 kwargs={})
    ]

    @property
    def _url_prefix(self):
        # NOTE(morgan): Override the parent class, this is a special case where
        # we do not want to prefix /v3.
        return self._url_prefix


APIs = (DiscoveryRootAPI,)
