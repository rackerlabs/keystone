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

import os


from keystone.common import utils as ks_utils
import keystone.conf
from keystone.federation import constants as federation_constants
from keystone.i18n import _
from keystone.token.providers import common
from keystone.token import token_formatters as tf


CONF = keystone.conf.CONF


class Provider(common.BaseProvider):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)

        # NOTE(lbragstad): We add these checks here because if the fernet
        # provider is going to be used and either the `key_repository` is empty
        # or doesn't exist we should fail, hard. It doesn't make sense to start
        # keystone and just 500 because we can't do anything with an empty or
        # non-existant key repository.
        if not os.path.exists(CONF.fernet_tokens.key_repository):
            subs = {'key_repo': CONF.fernet_tokens.key_repository}
            raise SystemExit(_('%(key_repo)s does not exist') % subs)
        if not os.listdir(CONF.fernet_tokens.key_repository):
            subs = {'key_repo': CONF.fernet_tokens.key_repository}
            raise SystemExit(_('%(key_repo)s does not contain keys, use '
                               'keystone-manage fernet_setup to create '
                               'Fernet keys.') % subs)

        self.token_formatter = tf.TokenFormatter()

    def issue_token(self, *args, **kwargs):
        token_id, token_data = super(Provider, self).issue_token(
            *args, **kwargs)
        self._build_issued_at_info(token_id, token_data)
        return token_id, token_data

    def _build_issued_at_info(self, token_id, token_data):
        # NOTE(roxanaghe, lbragstad): We must use the creation time that
        # Fernet builds into it's token. The Fernet spec details that the
        # token creation time is built into the token, outside of the payload
        # provided by Keystone. This is the reason why we don't pass the
        # issued_at time in the payload. This also means that we shouldn't
        # return a token reference with a creation time that we created
        # when Fernet uses a different creation time. We should use the
        # creation time provided by Fernet because it's the creation time
        # that we have to rely on when we validate the token.
        fernet_creation_datetime_obj = self.token_formatter.creation_time(
            token_id)
        if token_data.get('access'):
            token_data['access']['token']['issued_at'] = ks_utils.isotime(
                at=fernet_creation_datetime_obj, subsecond=True)
        else:
            token_data['token']['issued_at'] = ks_utils.isotime(
                at=fernet_creation_datetime_obj, subsecond=True)

    def _rebuild_federated_info(self, federated_dict, user_id):
        """Format federated information into the token reference.

        The federated_dict is passed back from the federated token formatters.
        The responsibility of this method is to format the information passed
        back from the token formatter into the token reference before
        constructing the token data from the V3TokenDataHelper.

        """
        g_ids = federated_dict['group_ids']
        idp_id = federated_dict['idp_id']
        protocol_id = federated_dict['protocol_id']

        federated_info = {
            'groups': g_ids,
            'identity_provider': {'id': idp_id},
            'protocol': {'id': protocol_id}
        }

        user_dict = self.identity_api.get_user(user_id)
        user_name = user_dict['name']

        token_dict = {
            'user': {
                federation_constants.FEDERATION: federated_info,
                'id': user_id,
                'name': user_name,
                'domain': {'id': CONF.federation.federated_domain_name,
                           'name': CONF.federation.federated_domain_name, },
            }
        }

        return token_dict

    def _rebuild_federated_token_roles(self, token_dict, federated_dict,
                                       user_id, project_id, domain_id):
        """Populate roles based on (groups, project/domain) pair.

        We must populate roles from (groups, project/domain) as ephemeral users
        don't exist in the backend. Upon success, a ``roles`` key will be added
        to ``token_dict``.

        :param token_dict: dictionary with data used for building token
        :param federated_dict: federated information such as identity provider
            protocol and set of group IDs
        :param user_id: user ID
        :param project_id: project ID the token is being scoped to
        :param domain_id: domain ID the token is being scoped to

        """
        group_ids = [x['id'] for x in federated_dict['group_ids']]
        self.v3_token_data_helper.populate_roles_for_federated_user(
            token_dict, group_ids, project_id, domain_id, user_id)

    def generate_token_id(self, token):
        # FIXME(lbragstad): The only reason why we pass a dictionary here is
        # becuase token creation was dependent on using attributes from the
        # token reference. Now that we have a token model, we can ask the
        # object about it's properties and whatnot instead of different parts
        # of keystone expecting a specific data structure like this one. The
        # end result should be more readable and understandable because it
        # reads like business logic.
        federated_info = None
        if token.is_federated:
            federated_info = {
                'group_ids': token.groups,
                'idp_id': token.identity_provider['id'],
                'protocol_id': token.protocol['id']
            }
        token.id = self.token_formatter.create_token(
            token.user_id,
            token.expires_at,
            token.audit_ids,
            methods=token.methods,
            system=token.system,
            domain_id=token.domain_id,
            project_id=token.project_id,
            trust_id=token.trust_id,
            federated_info=federated_info,
            access_token_id=token.access_token_id
        )
        creation_datetime_obj = self.token_formatter.creation_time(token.id)
        token.issued_at = ks_utils.isotime(
            at=creation_datetime_obj, subsecond=True
        )

    @property
    def _supports_bind_authentication(self):
        """Return if the token provider supports bind authentication methods.

        :returns: False

        """
        return False
