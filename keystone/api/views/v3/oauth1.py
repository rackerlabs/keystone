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
from keystone.api.views.v3 import role as role_view


class OAuth1BaseView(base.View):

    @property
    def collection_path(self):
        return '/OS-OAUTH1/%s' % self.collection_name


class ConsumerView(OAuth1BaseView):

    collection_name = 'consumers'
    member_name = 'consumer'

    required_params = [
        'id',
    ]

    optional_params = [
        'description',
        'secret',
    ]

    def render(self, obj, include_secret=False):
        output = super(ConsumerView, self).render(obj)
        if not include_secret:
            output.pop('secret', None)
        return output

    def create(self, obj):
        return super(ConsumerView, self).create(obj, include_secret=True)


class AccessTokenView(OAuth1BaseView):

    collection_name = 'access_tokens'
    member_name = 'access_token'

    def member_path(self, obj):
        tmpl = '/users/%(authorizing_user_id)s/OS-OAUTH1/access_tokens/%(id)s'
        return tmpl % obj

    def render(self, obj):
        output = super(AccessTokenView, self).render(obj)

        output.pop('role_ids', None)
        output.pop('access_secret', None)

        links = output.setdefault('links', {})
        links['roles'] = self.member_url(obj) + '/roles'

        return output


class AccessTokenRoles(role_view.RoleView):

    def render(self, obj):
        output = super(AccessTokenRoles, self).render(obj)

        output.pop('description', None)
        output.pop('enabled', None)

        return output
