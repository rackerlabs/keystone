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

"""Unified in-memory token model."""

import six

from keystone.common import config
from keystone.openstack.common import timeutils
from keystone.token import provider


CONF = config.CONF
V2 = provider.V2
V3 = provider.V3


def _parse_and_normalize_time(time_data):
    if isinstance(time_data, six.string_types):
        time_data = timeutils.parse_isotime(time_data)
    return timeutils.normalize_time(time_data)


class KeystoneToken(dict):
    """An in-memory representation that unifies v2 and v3 tokens."""
    # TODO(morganfainberg): Align this in-memory representation with the
    # objects in keystoneclient. This object should be eventually updated
    # to be the source of token data with the ability to emit any version
    # of the token instead of only consuming the token dict and providing
    # property accessors for the underlying data.

    def __init__(self, token_data):
        if 'access' in token_data:
            super(KeystoneToken, self).__init__(**token_data['access'])
            self.version = V2
        elif 'token' in token_data and 'methods' in token_data['token']:
            super(KeystoneToken, self).__init__(**token_data['token'])
            self.version = V3
        else:
            raise provider.UnsupportedTokenVersionException()

    @property
    def expires(self):
        if self.version is V3:
            expires_at = self['expires_at']
        else:
            expires_at = self['token']['expires']
        return _parse_and_normalize_time(expires_at)

    @property
    def issued(self):
        if self.version is V3:
            issued_at = self['issued_at']
        else:
            issued_at = self['token']['issued_at']
        return _parse_and_normalize_time(issued_at)

    @property
    def auth_token(self):
        if self.version is V3:
            return self['auth_token']
        else:
            return self['token']['id']

    @property
    def user_id(self):
        return self['user']['id']

    @property
    def user_name(self):
        return self['user']['name']

    @property
    def user_domain_name(self):
        return self['user']['domain']['name']

    @property
    def user_domain_id(self):
        return self['user']['domain']['id']

    @property
    def domain_id(self):
        if self.version is V3:
            return self['domain']['id']
        return None

    @property
    def domain_name(self):
        if self.version is V3:
            return self['domain']['name']
        return None

    @property
    def project_id(self):
        if self.version is V3:
            return self.get('project', {}).get('id')
        else:
            return self.get('tenant', {}).get('id')

    @property
    def project_domain_id(self):
        if self.version is V3:
            return self.get('project', {}).get('domain', {}).get('id')
        return CONF.identity.default_domain_id

    @property
    def project_domain_name(self):
        if self.version is V3:
            return self.get('project', {}).get('domain', {}).get('id')
        return 'Default'

    @property
    def project_scoped(self):
        if self.version is V3:
            return 'project' in self
        else:
            return 'tenant' in self

    @property
    def domain_scoped(self):
        if self.version is V3:
            return 'domain' in self
        return False

    @property
    def scoped(self):
        return self.domain_scoped or self.project_scoped

    @property
    def project_name(self):
        if self.version is V3:
            return self.get('project', {}).get('name')
        else:
            return self.get('tenant', {}).get('name')

    @property
    def trust_id(self):
        if self.version is V3:
            return self.get('OS-TRUST:trust', {}).get('id')
        else:
            return self.get('trust', {}).get('id')

    @property
    def trust_scoped(self):
        if self.version is V3:
            return 'OS-TRUST:trust' in self
        else:
            return 'trust' in self

    @property
    def trustee_user_id(self):
        if self.version is V3:
            return self.get(
                'OS-TRUST:trust', {}).get('trustee_user', {}).get('id')
        else:
            return self.get('trust', {}).get('trustee_user', {}).get('id')

    @property
    def trustor_id(self):
        if self.version is V3:
            return self.get(
                'OS-TRUST:trust', {}).get('trustor_user', {}).get('id')
        else:
            return self.get('trust', {}).get('trustor_user', {}).get('id')

    @property
    def oauth_access_token_id(self):
        if self.version is V3:
            return self.get('OS-OAUTH1', {}).get('access_token_id')
        return None

    @property
    def oauth_consumer_id(self):
        if self.version is V3:
            return self.get('OS-OAUTH1', {}).get('consumer_id')
        return None

    @property
    def role_ids(self):
        if self.version is V3:
            return [r['id'] for r in self.get('roles', [])]
        else:
            return self.get('metadata', {}).get('roles', [])

    @property
    def role_names(self):
        if self.version is V3:
            return [r['name'] for r in self.get('roles'), []]
        else:
            return [r['name'] for r in self['user'].get('roles', [])]
