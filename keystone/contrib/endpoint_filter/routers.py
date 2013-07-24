# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

from keystone.common import wsgi
from keystone.contrib.endpoint_filter import controllers


class EndpointFilterExtension(wsgi.ExtensionRouter):
    def add_routes(self, mapper):
        ep_filter_controller = controllers.EndpointFilterV3Controller()
        mapper.connect('/OS-EP-FILTER/endpoints/{endpoint_id}/projects',
                       controller=ep_filter_controller,
                       action='list_associated_projects',
                       conditions=dict(method=['GET']))
        mapper.connect('/OS-EP-FILTER/projects/{project_id}'
                       '/endpoints/{endpoint_id}',
                       controller=ep_filter_controller,
                       action='create_ep_filter_association',
                       conditions=dict(method=['PUT']))
        mapper.connect('/OS-EP-FILTER/projects/{project_id}'
                       '/endpoints/{endpoint_id}',
                       controller=ep_filter_controller,
                       action='check_ep_filter_association',
                       conditions=dict(method=['HEAD']))
        mapper.connect('/OS-EP-FILTER/projects/{project_id}/endpoints',
                       controller=ep_filter_controller,
                       action='get_ep_filter_associations',
                       conditions=dict(method=['GET']))
        mapper.connect('/OS-EP-FILTER/projects/{project_id}'
                       '/endpoints/{endpoint_id}',
                       controller=ep_filter_controller,
                       action='remove_ep_filter_association',
                       conditions=dict(method=['DELETE']))
