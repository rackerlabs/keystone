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

from keystone.api.views.v3 import base


class EndpointView(base.View):

    collection_name = 'endpoints'
    member_name = 'endpoint'

    required_params = [
        'id',
        'service_id',
        'interface',
        'url',
    ]

    optional_params = [
        'region_id',
        'enabled',
    ]

    def render(self, obj):
        output = super(EndpointView, self).render(obj)
        output.pop('legacy_endpoint_id', None)
        output['region'] = output['region_id']
        return output


class EndpointGroupView(base.View):

    collection_name = 'endpoint_groups'
    member_name = 'endpoint_group'

    @property
    def collection_path(self):
        return '/OS-EP-FILTER/%s' % self.collection_name


class ProjectEndpointGroupView(base.View):

    collection_name = 'project_endpoint_groups'
    member_name = 'project_endpoint_group'

    def member_path(self, obj):
        return '/'.join(['OS-EP-FILTER',
                         'endpoint_groups',
                         obj['endpoint_group_id'],
                         'projects',
                         obj['project_id']])
