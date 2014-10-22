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

from keystone import config
from keystone import exception
from keystone.openstack.common import log
from keystone.token.providers import common


CONF = config.CONF
LOG = log.getLogger(__name__)


class Provider(common.BaseProvider):

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

        :param user_id: ID of the user
        :param method_names:
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
        raise exception.NotImplemented()

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
        raise exception.NotImplemented()

    def _get_token_id(self, token_data):
        """Generate the token_id based upon the data in token_data.

        :param token_data: token information
        :type token_data: dict
        returns: token identifier
        """
        raise exception.NotImplemented()
