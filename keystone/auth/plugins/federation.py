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

import urllib

from keystone import auth
from keystone.common import dependency
from keystone import config
from keystone.contrib.federation import core as federation
from keystone.contrib.federation import utils
from keystone import exception
from keystone.openstack.common import log
from keystone.openstack.common import timeutils


CONF = config.CONF
LOG = log.getLogger(__name__)


@dependency.requires('token_api', 'federation_api')
class Federation(auth.AuthMethodHandler):

    method = 'federation'

    def __init__(self):
        self.federation_api = federation.Manager()

    def authenticate(self, context, auth_info, auth_context):
        """Turn unscoped federated token to a valid, scoped one."""
        try:
            federated_token_id = auth_info['id']
        except KeyError:
            raise exception.ValidationError(
                attribute='federated_token', target=self.method)
        token_ref = self.token_api.get_token(federated_token_id)
        auth_context['expires_at'] = self._validate_expiration(token_ref)
        auth_context['user_id'] = token_ref['user_id']
        auth_context['federated_token'] = token_ref

    def get_unscoped_token(self, context, identity_provider, protocol):
        """Handle request to return an unscoped token for federation."""

        #TODO(marek-denis): Uncomment below when mapping engine is ready
        #assertion = dict(self._get_assertion_params_from_env(context))
        #assertion_processor = utils.AssertionProcessor(assertion)
        #mapping_ref = self.get_mapping_from_idp_and_protocol(idp, protocol)

        mapped_user_groups_ids = utils.map_assertion(context)
        token_data = self._create_token_data(mapped_user_groups_ids,
                                             identity_provider,
                                             protocol)
        return token_data

    def _get_assertion_params_from_env(self, context):
        prefix = CONF.federation.assertion_prefix
        for k, v in context['environment'].iteritems():
            if k.startswith(prefix):
                yield (k, v)

    def _url(self, identity_provider, protocol):
        idp_proto = {
            'idp': identity_provider,
            'proto': protocol
        }
        path = ("/OS-FEDERATION/identity_providers/"
                "%(idp)s/protocols/%(proto)s" % idp_proto)
        return path

    def _refactor_group_ids(self, groups):
        return [{'id': x} for x in groups]

    def _create_token_data(self, mapped_properties, identity_provider,
                           protocol):
        """Create a token data.

        Assume the mapped_properties are in a format:
            {
                'name': 'foobar',
                'group_ids': ['abc123', 'def456']
            }

        """

        entity = {
            'user': {
                'id': urllib.quote(mapped_properties['name']),
                'name': mapped_properties['name'],
                'groups': self._refactor_group_ids(
                    mapped_properties['group_ids']),
                'OS-FEDERATION:protocol': {
                    'links': {
                        'self': self._url(identity_provider, protocol)
                    }
                }
            }
        }

        return entity

    def _validate_expiration(self, token_ref):
        expires_at = token_ref['expires']
        if expires_at:
            now = timeutils.utcnow()
#            expires = timeutils.normalize_time(
#                timeutils.parse_isotime(expires_at))
            if now > expires_at:
                raise exception.Unauthorized(_('Federation token is expired'))
        return expires_at
