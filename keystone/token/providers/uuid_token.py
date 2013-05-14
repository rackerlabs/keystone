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

from keystone.common import dependency
from keystone.common import logging
from keystone import config
from keystone import exception
from keystone.openstack.common import timeutils
from keystone.token import provider as token_provider


LOG = logging.getLogger(__name__)
CONF = config.CONF


@dependency.requires('token_api', 'identity_api')
class Provider(token_provider.Driver):
    def __inti__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        if CONF.trust.enabled:
            self.trust_api = trust.Manager()

    def _get_token_id(self, token_data):
        return uuid.uuid4().hex

    def issue_token(self, user_id, method_names, expires_at=None,
                    project_id=None, domain_id=None,
                    auth_context=None, **kwargs):
        token_data_helper = token_provider.TokenDataHelper(None)
        trust = kwargs.get('trust')
        metadata_ref = kwargs.get('metadata_ref')
        #FIXME(gyee): for V2, trust is stashed in metadata_ref
        if not trust and metadata_ref and 'trust_id' in metadata_ref:
            trust = self.trust_api.get_trust(None, metadata_ref['trust_id'])
        token_data = token_data_helper.get_token_data(
            user_id,
            method_names,
            auth_context.get('extras') if auth_context else None,
            domain_id,
            project_id,
            expires_at,
            metadata_ref,
            trust)

        token_id = self._get_token_id(token_data)
        try:
            expiry = token_data['token']['expires_at']
            if isinstance(expiry, basestring):
                expiry = timeutils.normalize_time(
                    timeutils.parse_isotime(expiry))
            # FIXME(gyee): is there really a need to store roles in metadata?
            role_ids = []
            metadata_ref = kwargs.get('metadata_ref', {})
            if 'project' in token_data['token']:
                # project-scoped token, fill in the v2 token data
                # all we care are the role IDs
                role_ids = [r['id'] for r in token_data['token']['roles']]
                metadata_ref = {'roles': role_ids}
            if trust:
                metadata_ref.setdefault('trust_id', trust['id'])
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
        token_version = token_provider.get_token_version(token_data)
        if token_version == token_provider.V3:
            if 'catalog' in token_data['token']:
                del token_data['token']['catalog']
        if token_version == token_provider.V2:
            if 'serviceCatalog' in token_data['access']:
                del token_data['access']['serviceCatalog']

    def _assert_not_domain_scoped(self, token_data):
        # domain scoping is prohibited
        if token_data['token'].get('domain'):
            raise exception.Unauthorized(
                _('Domain scoped token is not supported'))

    def _assert_belongs_to_domain(self, context, belongs_to_domain, token_data,
                                  metadata_ref=None):
        """ Make sure token is valid on the given domain only. """
        msg = _('token is only valid for domain %s') % (belongs_to_domain)
        if (token_data['token']['user']['domain']['id'] !=
                belongs_to_domain):
            raise exception.Unauthorized(msg)
        if ('domain' in token_data['token'] and
                token_data['token']['domain']['id'] !=
                belongs_to_domain):
            raise exception.Unauthorized(msg)
        if ('project' in token_data['token'] and
                token_data['token']['project']['domain']['id'] !=
                belongs_to_domain):
            raise exception.Unauthorized(msg)
        # if token is scoped to trust, both trustor and trustee must
        # be in the default domain. Furthermore, the delegated project
        # must also be in the default domain
        if CONF.trust.enabled and metadata_ref and 'trust_id' in metadata_ref:
            trust_ref = self.trust_api.get_trust(context,
                                                 metadata_ref['trust_id'])
            trustee_user_ref = self.identity_api.get_user(
                context, trust_ref['trustee_user_id'])
            if trustee_user_ref['domain_id'] != belongs_to_domain:
                raise exception.Unauthorized(msg)
            trustor_user_ref = self.identity_api.get_user(
                context, trust_ref['trustor_user_id'])
            if trustor_user_ref['domain_id'] != belongs_to_domain:
                raise exception.Unauthorized(msg)
            project_ref = self.identity_api.get_project(
                context, trust_ref['project_id'])
            if project_ref['domain_id'] != belongs_to_domain:
                raise exception.Unauthorized(msg)

    def validate_token(self, token_id, belongs_to=None,
                       belongs_to_domain=None, no_domain_scope=False,
                       **kwargs):
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
                token_data_helper = token_provider.TokenDataHelper(None)
                token_data = token_data_helper.get_token_data(
                    user_id=token_ref['user']['id'],
                    method_names=['password', 'token'],
                    extras={},
                    domain_id=None,
                    project_id=project_id,
                    expires=token_ref['expires'],
                    trust=None)
            if belongs_to_domain:
                self._assert_belongs_to_domain(None,
                                               belongs_to_domain,
                                               token_data,
                                               token_ref.get('metadata_ref'))
            if no_domain_scope:
                self._assert_not_domain_scoped(token_data)
            #if not kwargs.get('need_catalog', True):
            #    self._remove_service_catalog_from_token_data(token_data)
            return token_data
        except Exception as e:
            LOG.exception(e)
            raise exception.Unauthorized(e)

    def check_token(self, token_id, belongs_to=None,
                    belongs_to_domain=None, no_domain_scope=False,
                    **kwargs):
        try:
            if belongs_to_domain or no_domain_scope:
                self.validate_token(token_id, belongs_to, belongs_to_domain,
                                    no_domain_scope, **kwargs)
            else:
                token_ref = self.token_api.get_token(None,
                                                     token_id=token_id)
                self._verify_token(token_ref, belongs_to)
        except Exception as e:
            LOG.exception(e)
            raise exception.Unauthorized(e)
