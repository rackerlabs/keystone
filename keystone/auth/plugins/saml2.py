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

from keystone import auth
from keystone.common import dependency
from keystone import config
from keystone.contrib.federation import core as federation
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

    def __init__(self):
        self.federation_api = federation.Manager()

    def authenticate(self, context, auth_info, auth_context):
        if auth_info.get('id') is not None:
            self._handle_scoped_token(context, auth_info, auth_context)
        else:
            self._handle_unscoped_token(context, auth_info, auth_context)

    def _handle_scoped_token(self, context, auth_info, auth_context):
        token_ref = self.token_api.get_token(auth_info['id'])
        self._validate_expiration(token_ref)
        auth_context['user_id'] = token_ref['user_id']
        auth_context['federated_token'] = token_ref

    def _handle_unscoped_token(self, context, auth_info, auth_context):
        assertion = dict(self._get_assertion_params_from_env(context))

        identity_provider = auth_info['identity_provider']
        protocol = auth_info['protocol']

        mapping = self.federation_api.get_mapping_from_idp_and_protocol(
            identity_provider, protocol)
        rules = jsonutils.loads(mapping.get('rules', {}))
        rule_processor = utils.RuleProcessor(rules.get('rules'))
        mapped_properties = rule_processor.process(assertion)
        if mapped_properties.get('name') is None:
            msg = _("Could not map assertion")
            raise exception.Unauthorized(msg)
        auth_context['project_id'] = None
        auth_context['user_id'] = mapped_properties.get('name')
        auth_context['group_ids'] = mapped_properties['group_ids']

    def _get_assertion_params_from_env(self, context):
        prefix = CONF.federation.assertion_prefix
        for k, v in context['environment'].iteritems():
            if k.startswith(prefix):
                yield (k, v)

    def _validate_expiration(self, token_ref):
        expires_at = token_ref['expires']
        if expires_at and timeutils.utcnow() > expires_at:
            raise exception.Unauthorized(_('Federation token is expired'))
