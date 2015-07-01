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

from oslo_config import cfg
from oslo_log import log

from keystone.common import dependency
from keystone.contrib import federation
from keystone import exception
from keystone.i18n import _
from keystone.token import provider
from keystone.token.providers import common
from keystone.token.providers.fernet import token_formatters as tf


CONF = cfg.CONF
LOG = log.getLogger(__name__)


@dependency.requires('trust_api')
class Provider(common.BaseProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)

        self.token_formatter = tf.TokenFormatter()

    def needs_persistence(self):
        """Should the token be written to a backend."""
        return False

    def _build_federated_info(self, token_data):
        """Extract everything needed for federated tokens.

        This dictionary is passed to the FederatedPayload token formatter,
        which unpacks the values and builds the Fernet token.

        """
        group_ids = token_data['token'].get('user', {}).get(
            federation.FEDERATION, {}).get('groups')
        idp_id = token_data['token'].get('user', {}).get(
            federation.FEDERATION, {}).get('identity_provider', {}).get('id')
        protocol_id = token_data['token'].get('user', {}).get(
            federation.FEDERATION, {}).get('protocol', {}).get('id')
        if not group_ids:
            group_ids = list()
        if group_ids:
            federated_dict = dict(group_ids=group_ids, idp_id=idp_id,
                                  protocol_id=protocol_id)
            return federated_dict
        return None

    def _rebuild_federated_info(self, federated_dict, user_id):
        """Format federated information into the token reference.

        The federated_dict is passed back from the FederatedPayload token
        formatter. The responsibility of this method is to format the
        information passed back from the token formatter into the token
        reference before constructing the token data from the
        V3TokenDataHelper.

        """
        g_ids = federated_dict['group_ids']
        idp_id = federated_dict['idp_id']
        protocol_id = federated_dict['protocol_id']
        federated_info = dict(groups=g_ids,
                              identity_provider=dict(id=idp_id),
                              protocol=dict(id=protocol_id))
        token_dict = {'user': {federation.FEDERATION: federated_info}}
        token_dict['user']['id'] = user_id
        token_dict['user']['name'] = user_id
        return token_dict

    # FIXME(lbragstad): Consolidate this into BaseProvider.validate_v2_token()
    def validate_v2_token(self, token_ref):
        """Validate a V2 formatted token.

        :param token_ref: reference describing the token to validate
        :returns: the token data
        :raises keystone.exception.Unauthorized: if v3 token is used

        """
        (user_id, methods,
         audit_ids, domain_id,
         project_id, trust_id,
         federated_info, created_at,
         expires_at) = self.token_formatter.validate_token(token_ref)

        if trust_id or domain_id or federated_info:
            msg = _('This is not a v2.0 Fernet token. Use v3 for trust, '
                    'domain, or federated tokens.')
            raise exception.Unauthorized(msg)

        v3_token_data = self.v3_token_data_helper.get_token_data(
            user_id,
            methods,
            project_id=project_id,
            expires=expires_at,
            issued_at=created_at,
            token=token_ref,
            include_catalog=False,
            audit_info=audit_ids)
        return self.v2_token_data_helper.v3_to_v2_token(token_ref,
                                                        v3_token_data)

    def _extract_v2_token_data(self, token_data):
        user_id = token_data['access'].get('user', {}).get('id')
        expires_at = token_data['access']['token']['expires']
        audit_ids = token_data['access']['token'].get('audit_ids')
        methods = ['password']
        if audit_ids:
            parent_audit_id = token_data['access']['token'].get(
                'parent_audit_id')
            audit_ids = provider.audit_info(parent_audit_id)
            if parent_audit_id:
                methods.append('token')
        project_id = token_data['access']['token'].get('tenant', {}).get('id')
        domain_id = None
        trust_id = None
        federated_info = None
        return (user_id, expires_at, audit_ids, methods, domain_id, project_id,
                trust_id, federated_info)

    def _extract_v3_token_data(self, token_data):
        """Extract information from a v3 token reference."""
        user_id = token_data['token'].get('user', {}).get('id')
        expires_at = token_data['token']['expires_at']
        audit_ids = token_data['token']['audit_ids']
        methods = token_data['token'].get('methods')
        domain_id = token_data['token'].get('domain', {}).get('id')
        project_id = token_data['token'].get('project', {}).get('id')
        trust_id = token_data['token'].get('OS-TRUST:trust', {}).get('id')
        federated_info = self._build_federated_info(token_data)

        return (user_id, expires_at, audit_ids, methods, domain_id, project_id,
                trust_id, federated_info)

    def _get_token_id(self, token_data):
        """Generate the token_id based upon the data in token_data.

        :param token_data: token information
        :type token_data: dict
        :raises keystone.exception.NotImplemented: when called
        """
        if token_data.get('access'):
            (user_id, expires_at, audit_ids, methods, domain_id, project_id,
                trust_id, federated_info) = self._extract_v2_token_data(
                    token_data)
        else:
            (user_id, expires_at, audit_ids, methods, domain_id, project_id,
                trust_id, federated_info) = self._extract_v3_token_data(
                    token_data)

        return self.token_formatter.create_token(user_id,
                                                 expires_at,
                                                 audit_ids,
                                                 methods=methods,
                                                 domain_id=domain_id,
                                                 project_id=project_id,
                                                 trust_id=trust_id,
                                                 federated_info=federated_info)

    @property
    def _supports_bind(self):
        """The Fernet token provider doesn't support bind authentication.

        :raises keystone.exception.NotImplemented:
        """
        raise exception.NotImplemented()
