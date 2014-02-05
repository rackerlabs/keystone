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

from six.moves.urllib import parse

from keystone import auth
from keystone.common import dependency
from keystone import config
from keystone.contrib.federation import utils
from keystone import exception
from keystone.openstack.common import jsonutils
from keystone.openstack.common import log
from keystone.openstack.common import timeutils


CONF = config.CONF
LOG = log.getLogger(__name__)


@dependency.requires('token_api', 'federation_api')
class Saml2(auth.AuthMethodHandler):

    method = 'saml2'

    def authenticate(self, context, auth_payload, auth_context):
        """Authenticate federated user and return an authentication context.

        :param context: keystone's request context
        :auth_payload: the content of the authentication for a given method
        :auth_context: user authentication context, a dictionary shared
                       by all plugins.

        In addition to ``user_id`` in ``auth_context``, the ``saml2`` plugin
        also sets ``group_ids``, ``identity_provider`` and ``protocol``.
        These values are required for issuing an unscoped federated token.
        When scoping the federated tokens, the plugin sets
        ``federated_token``, this entry stores the unscoped token.

        """

        if 'id' in auth_payload:
            self._handle_scoped_token(auth_context, auth_payload)
        else:
            self._handle_unscoped_token(context, auth_context, auth_payload)

    def _handle_scoped_token(self, auth_context, auth_payload):
        token_ref = self.token_api.get_token(auth_payload['id'])
        self._validate_expiration(token_ref)
        auth_context['user_id'] = token_ref['user_id']
        groups = token_ref['user']['OS-FEDERATION:groups']
        auth_context['group_ids'] = [x['id'] for x in groups]

    def _handle_unscoped_token(self, context, auth_context, auth_payload):
        assertion = context['environment']

        identity_provider = auth_payload['identity_provider']
        protocol = auth_payload['protocol']

        mapping = self.federation_api.get_mapping_from_idp_and_protocol(
            identity_provider, protocol)
        rules = jsonutils.loads(mapping['rules'])
        rule_processor = utils.RuleProcessor(rules)
        mapped_properties = rule_processor.process(assertion)
        auth_context['user_id'] = parse.quote(mapped_properties['name'])
        auth_context['group_ids'] = mapped_properties['group_ids']
        auth_context['OS-FEDERATION:identity_provider'] = identity_provider
        auth_context['OS-FEDERATION:protocol'] = protocol

    def _validate_expiration(self, token_ref):
        if timeutils.utcnow() > token_ref['expires']:
            raise exception.Unauthorized(_('Federation token is expired'))
