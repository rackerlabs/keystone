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


class FederationBaseView(base.View):

    include_extras = False

    @property
    def collection_path(self):
        return '/OS-FEDERATION/%s' % self.collection_name


class IdentityProviderView(FederationBaseView):

    collection_name = 'identity_providers'
    member_name = 'identity_provider'

    required_params = [
        'id',
    ]

    optional_params = [
        'description',
        'enabled',
        'remote_ids',
    ]

    def render(self, obj):
        output = super(IdentityProviderView, self).render(obj)

        links = output.setdefault('links', {})
        links['protocols'] = self.member_url(obj) + '/protocols'

        return output


class ProtocolView(FederationBaseView):

    collection_name = 'protocols'
    member_name = 'protocol'

    required_params = [
        'id',
        'mapping_id'
    ]

    def idp_path(self, obj):
        return '/OS-FEDERATION/identity_providers/%s' % obj['idp_id']

    def member_path(self, obj):
        return '%s/protocols/%s' % (self.idp_path(obj), obj['id'])

    def render(self, obj):
        output = super(ProtocolView, self).render(obj)

        links = output.setdefault('links', {})
        links['identity_provider'] = self.host_url + self.idp_path(obj)

        return output


class MappingView(FederationBaseView):

    collection_name = 'mappings'
    member_name = 'mapping'

    required_params = [
        'id',
        'rules',
    ]


class ServiceProviderView(FederationBaseView):

    collection_name = 'service_providers'
    member_name = 'service_provider'

    required_params = [
        'auth_url',
        'id',
        'sp_url',
    ]

    optional_params = [
        'description',
        'enabled',
        'relay_state_prefix'
    ]
