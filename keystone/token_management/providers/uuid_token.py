# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack LLC
#
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

"""UUID Token Provider"""

import uuid

from keystone.common import logging
from keystone import config
from keystone import exception
from keystone import identity
from keystone import token
from keystone import token_management
from keystone import trust
from keystone.openstack.common import timeutils


LOG = logging.getLogger(__name__)
CONF = config.CONF
DEFAULT_DOMAIN_ID = CONF.identity.default_domain_id


class UuidToken(token_management.Driver):
    def __init__(self, *args, **kwargs):
        super(UuidToken, self).__init__(*args, **kwargs)
        self.token_api = token.Manager()
        self.trust_api = trust.Manager()
        self.identity_api = identity.Manager()

    def _get_token_id(self, token_data):
        return uuid.uuid4().hex

    def issue_v2_token(self, user_id, expires=None, project_id=None,
                       metadata_ref=None):
        token_data_helper = token_management.V2TokenDataHelper(None)
        token_data = token_data_helper.get_token_data(
            user_id=user_id,
            expires=expires,
            project_id=project_id,
            metadata_ref=metadata_ref)
        token_id = self._get_token_id(token_data)
        token_data['access']['token']['id'] = token_id
        try:
            expiry = token_data['access']['token']['expires']
            if isinstance(expiry, basestring):
                expiry = timeutils.normalize_time(
                    timeutils.parse_isotime(expiry))
            trust_id = None
            if 'trust_id' in metadata_ref:
                trust_id = metadata_ref['trust_id']
            # TODO(gyee): we should really be storing the hash of the
            # PKI token ID instead.
            # token_id = token_module(token_id)

            data = dict(key=token_id,
                        id=token_id,
                        expires=expiry,
                        user=token_data['access']['user'],
                        tenant=token_data['access']['token'].get('tenant'),
                        metadata=metadata_ref,
                        token_data=token_data,
                        trust_id=trust_id)
            self.token_api.create_token(None, token_id, data)
        except Exception as e:
            # an identical token may have been created already.
            # if so, return the token_data as it is also identical
            try:
                self.token_api.get_token(None,
                                         token_id=token_id)
            except exception.TokenNotFound:
                raise e

        return token_data

    def issue_v3_token(self, user_id, method_names, expires_at=None,
                       project_id=None, domain_id=None, trust=None,
                       auth_context=None, **kwargs):
        token_data_helper = token_management.TokenDataHelper(None)
        token_data = token_data_helper.get_token_data(
            user_id,
            method_names,
            auth_context.get('extras'),
            domain_id,
            project_id,
            expires_at,
            trust)

        token_id = self._get_token_id(token_data)
        try:
            expiry = token_data['token']['expires_at']
            if isinstance(expiry, basestring):
                expiry = timeutils.normalize_time(
                    timeutils.parse_isotime(expiry))
            role_ids = []
            if 'project' in token_data['token']:
                # project-scoped token, fill in the v2 token data
                # all we care are the role IDs
                role_ids = [r['id'] for r in token_data['token']['roles']]
            metadata_ref = {'roles': role_ids}
            data = dict(key=token_id,
                        id=token_id,
                        expires=expiry,
                        user=token_data['token']['user'],
                        tenant=token_data['token'].get('project'),
                        metadata=metadata_ref,
                        token_data=token_data,
                        trust_id=trust['id'] if trust else None)
            self.token_api.create_token(None, token_id, data)
        except Exception as e:
            # an identical token may have been created already.
            # if so, return the token_data as it is also identical
            try:
                self.token_api.get_token(None,
                                         token_id=token_id)
            except exception.TokenNotFound:
                raise e

        return (token_id, token_data)

    def _verify_token(self, token_ref, belongs_to=None):
        assert token_ref
        if belongs_to:
            assert token_ref['tenant']['id'] == belongs_to

    def revoke_token(self, token_id):
        self.token_api.delete_token(None, token_id=token_id)

    def _remove_service_catalog_from_token_data(self, token_data):
        # FIXME(gyee): probably need a better indicator for token version
        if 'token' in token_data and 'methods' in token_data['token']:
            # this is a V3 token
            if 'catalog' in token_data['token']:
                del token_data['token']['catalog']
        if 'access' in token_data:
            # this is a V2 token
            if 'serviceCatalog' in token_data['access']:
                del token_data['access']['serviceCatalog']

    def _assert_default_domain(self, context, token_ref):
        """ Make sure we are operating on default domain only. """
        if token_ref.get('token_data'):
            # this is a V3 token
            msg = _('Non-default domain is not supported')
            # user in a non-default is prohibited
            if (token_ref['token_data']['token']['user']['domain']['id'] !=
                    DEFAULT_DOMAIN_ID):
                raise exception.Unauthorized(msg)
            # domain scoping is prohibited
            if token_ref['token_data']['token'].get('domain'):
                raise exception.Unauthorized(
                    _('Domain scoped token is not supported'))
            # project in non-default domain is prohibited
            if token_ref['token_data']['token'].get('project'):
                project = token_ref['token_data']['token']['project']
                project_domain_id = project['domain']['id']
                # scoped to project in non-default domain is prohibited
                if project_domain_id != DEFAULT_DOMAIN_ID:
                    raise exception.Unauthorized(msg)
            # if token is scoped to trust, both trustor and trustee must
            # be in the default domain. Furthermore, the delegated project
            # must also be in the default domain
            metadata_ref = token_ref['metadata']
            if CONF.trust.enabled and 'trust_id' in metadata_ref:
                trust_ref = self.trust_api.get_trust(context,
                                                     metadata_ref['trust_id'])
                trustee_user_ref = self.identity_api.get_user(
                    context, trust_ref['trustee_user_id'])
                if trustee_user_ref['domain_id'] != DEFAULT_DOMAIN_ID:
                    raise exception.Unauthorized(msg)
                trustor_user_ref = self.identity_api.get_user(
                    context, trust_ref['trustor_user_id'])
                if trustor_user_ref['domain_id'] != DEFAULT_DOMAIN_ID:
                    raise exception.Unauthorized(msg)
                project_ref = self.identity_api.get_project(
                    context, trust_ref['project_id'])
                if project_ref['domain_id'] != DEFAULT_DOMAIN_ID:
                    raise exception.Unauthorized(msg)

    def validate_v2_token(self, token_id, belongs_to=None):
        try:
            token_ref = self.token_api.get_token(None,
                                                 token_id=token_id)
            self._verify_token(token_ref, belongs_to)
            # FIXME(gyee): performance or correctness? Should we return the
            # cached token or reconstruct it? Obviously if we are going with
            # the cached token, any role, project, or domain name changes
            # will not be reflected. One may argue that with PKI tokens,
            # we are essentially doing cached token validation anyway.
            # Lets go with the cached token strategy. Since token
            # management layer is now pluggable, one can always provide
            # their own implementation to suit their needs.
            token_data = token_ref.get('token_data')
            if token_data and 'access' not in token_data:
                # this is a V3 token, make sure we are operation in the
                # default domain only
                self._assert_default_domain(None, token_ref)
            if not token_data or 'access' not in token_data:
                # token is created by V3 or legacy V2 API
                project_id = None
                project_ref = token_ref.get('tenant')
                if project_ref:
                    project_id = project_ref['id']
                token_data_helper = token_management.V2TokenDataHelper(None)
                token_data = token_data_helper.get_token_data(
                    user_id=token_ref['user']['id'],
                    expires=token_ref['expires'],
                    project_id=project_id,
                    metadata_ref=token_ref['metadata'])
                token_data['access']['token']['id'] = token_id
            return token_data
        except Exception as e:
            LOG.exception(e)
            raise exception.Unauthorized(e)

    def validate_v3_token(self, token_id, belongs_to=None, need_catalog=True):
        try:
            token_ref = self.token_api.get_token(None,
                                                 token_id=token_id)
            self._verify_token(token_ref, belongs_to)
            # FIXME(gyee): performance or correctness? Should we return the
            # cached token or reconstruct it? Obviously if we are going with
            # the cached token, any role, project, or domain name changes
            # will not be reflected. One may argue that with PKI tokens,
            # we are essentially doing cached token validation anyway.
            # Lets go with the cached token strategy. Since token
            # management layer is now pluggable, one can always provide
            # their own implementation to suit their needs.
            token_data = token_ref.get('token_data')
            if not token_data or 'token' not in token_data:
                # token ref is created by V2 API
                project_id = None
                project_ref = token_ref.get('tenant')
                if project_ref:
                    project_id = project_ref['id']
                token_data_helper = token_management.TokenDataHelper(None)
                token_data = token_data_helper.get_token_data(
                    user_id=token_ref['user']['id'],
                    method_names=['password', 'token'],
                    extras={},
                    domain_id=None,
                    project_id=project_id,
                    expires=token_ref['expires'],
                    trust=None)
            if not need_catalog:
                self._remove_service_catalog_from_token_data(token_data)
            return token_data
        except Exception as e:
            LOG.exception(e)
            raise exception.Unauthorized(e)

    def check_v2_token(self, token_id, belongs_to=None):
        try:
            token_ref = self.token_api.get_token(None,
                                                 token_id=token_id)
            self._verify_token(token_ref, belongs_to)
            token_data = token_ref.get('token_data')
            if token_data and 'access' not in token_data:
                # this is a V3 token, make sure we are operation in the
                # default domain only
                self._assert_default_domain(None, token_ref)
        except Exception as e:
            LOG.error(e)
            LOG.exception(e)
            raise exception.Unauthorized(e)

    def check_v3_token(self, token_id, belongs_to=None):
        try:
            token_ref = self.token_api.get_token(None,
                                                 token_id=token_id)
            self._verify_token(token_ref, belongs_to)
        except Exception as e:
            LOG.error(e)
            LOG.exception(e)
            raise exception.Unauthorized(e)
