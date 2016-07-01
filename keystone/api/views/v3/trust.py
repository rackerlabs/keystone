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


class TrustView(base.View):

    collection_name = 'trusts'
    member_name = 'trust'

    required_params = [
        'id',
        'trustor_user_id',
        'trustee_user_id',
        'impersonation',
    ]

    optional_params = [
        'project_id',
        'roles',
        'expires_at',
        'remaining_uses',
        'allow_redelegation',
        'redelegation_count',
        'redelegation_trust_id',
    ]

    @property
    def collection_path(self):
        return '/OS-TRUST/%s' % self.collection_name
