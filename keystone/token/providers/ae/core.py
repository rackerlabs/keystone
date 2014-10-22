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

import datetime

from keystone import config
from keystone import exception
from keystone.openstack.common import log
from keystone.token.providers import common
from keystone.token.providers.ae import token_formatters

CONF = config.CONF
LOG = log.getLogger(__name__)


class Provider(common.BaseProvider):

    # NOTE(lbragstad): This should consist of a mapping from the
    # `token_version` to the object that can handle that token. This is because
    # once we detect what version of the token we're dealing with, we can pass
    # the information to it's respective formatter to either create or
    # validate the token.
    token_format_map = {'AE01': token_formatters.StandardTokenFormatter()}

    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)

    def issue_v2_token(self, token_ref, roles_ref=None, catalog_ref=None):
        """Issue a V2 formatted token.

        :param token_ref: reference describing the token
        :param roles_ref: reference describing the roles for the token
        :catalog_ref: reference describing the token's catalog
        :return: tuple containing the id of the token and the token data

        """
        raise exception.NotImplemented()

    def issue_v3_token(self, user_id, method_names, expires_at=None,
                       project_id=None, domain_id=None, auth_context=None,
                       trust=None, metadata_ref=None, include_catalog=True,
                       parent_audit_id=None):
        """Issue a V3 formatted token.

        Here is where we need to detect what is given to us, and what kind of
        token the user is expect. Depending on the outcome of that, we can pass
        all the information to be packed to the proper token format handler.

        :param user_id: ID of the user
        :param method_names: method of authentication
        :param expires_at: token expiration time
        :param project_id: ID of the project being scoped to
        :param domain_id: ID of the domain being scoped to
        :param auth_context: authentication context
        :param trust: ID of the trust
        :param metadata_ref: metadata reference
        :param include_catalog: return the catalog in the response if True,
                                otherwise don't return the catalog
        :param parent_audit_id: ID of the patent audit entity
        :returns: tuple containing the id of the token and the token data

        """
        if (CONF.trust.enabled and not trust and metadata_ref and
                'trust_id' in metadata_ref):
            trust = self.trust_api.get_trust(metadata_ref['trust_id'])
            # In this case we should pull data out of the trust and create the
            # token accordingly. This will also be a different token version so
            # that we know we are dealing with a trust authenticated token when
            # we go to validate.

        token_ref = None
        if auth_context and self._is_mapped_token(auth_context):
            token_ref = self._handle_mapped_tokens(auth_context, project_id,
                    domain_id)

        token_data = self.v3_token_data_helper.get_token_data(
            user_id,
            method_names,
            auth_context.get('extras') if auth_context else None,
            domain_id=domain_id,
            project_id=project_id,
            expires=expires_at,
            trust=trust,
            bind=auth_context.get('bind') if auth_context else None,
            token=token_ref,
            include_catalog=include_catalog,
            audit_info=parent_audit_id)

        # We will probably have different token formats, each with their own
        # create_token method. Here is where we would make the decision to
        # format the token one way or the other.
        token_format = 'AE01'
        token_id = self.token_format_map[token_format].create_token(user_id,
            project_id, token_data)

        return token_id, token_data

    def validate_v2_token(self, token_ref):
        """Validate a V2 formatted token.

        :param token_ref: reference describing the token to validate
        :returns: the token data
        :raises: keystone.exception.TokenNotFound

        """
        raise exception.NotImplemented()

    def validate_v3_token(self, token_ref):
        """Validate a V3 formatted token.

        :param token_ref: a reference describing the token to validate
        :returns: the token data
        :raises: keystone.exception.TokenNotFound

        """
        token_format = token_ref[:4]
        token_str = token_ref[4:]
        token_formatter = self.token_format_map[token_format]
        (user_id, project_id, token_data) = token_formatter.validate_token(
                token_str)
        token_data = self.v3_token_data_helper.get_token_data(
            user_id,
            ['password', 'token'],
            {},
            project_id=project_id,
            expires=token_data['token']['expires_at'],
            issued_at=token_data['token']['issued_at'],
            audit_info=token_data['token']['audit_ids'])
        return token_data

    def _get_token_id(self, token_data):
        """Generate the token_id based upon the data in token_data.

        :param token_data: token information
        :type token_data: dict
        returns: token identifier
        """
        raise exception.NotImplemented()
