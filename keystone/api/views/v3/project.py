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


class ProjectView(base.View):

    collection_name = 'projects'
    member_name = 'project'

    required_params = [
        'id',
        'name',
    ]

    optional_params = [
        'is_domain',
        'parent_id',
        'domain_id',
        'description',
        'enabled',
        'parents',
        'subtree',
    ]
