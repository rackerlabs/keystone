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

import json
import uuid

from keystone.common import cms
from keystone.common import dependency
from keystone.common import environment
from keystone.common import logging
from keystone import config
from keystone import exception
from keystone.openstack.common import timeutils
from keystone import token
from keystone.token import provider as token_provider
from keystone import trust


LOG = logging.getLogger(__name__)
CONF = config.CONF
DEFAULT_DOMAIN_ID = CONF.identity.default_domain_id


@dependency.requires('catalog_api', 'identity_api')
class V3TokenDataHelper(object):
    """Token data helper."""
    def __init__(self, context):
        self.context = context
        if CONF.trust.enabled:
            self.trust_api = trust.Manager()

    def _get_filtered_domain(self, domain_id):
        domain_ref = self.identity_api.get_domain(self.context,
                                                  domain_id)
        return {'id': domain_ref['id'], 'name': domain_ref['name']}

    def _populate_scope(self, token_data, domain_id, project_id):
        if domain_id:
            token_data['domain'] = self._get_filtered_domain(domain_id)
        if project_id:
            project_ref = self.identity_api.get_project(
                self.context, project_id)
            filtered_project = {
                'id': project_ref['id'],
                'name': project_ref['name']}
            filtered_project['domain'] = self._get_filtered_domain(
                project_ref['domain_id'])
            token_data['project'] = filtered_project

    def _get_metadata_ref(self, user_id=None, tenant_id=None,
                          domain_id=None, group_id=None):
        """Returns metadata_ref for a user or group in a tenant or domain."""
        metadata_ref = {}
        if (user_id or group_id) and (tenant_id or domain_id):
            try:
                metadata_ref = self.identity_api.get_metadata(
                    context=self.context, user_id=user_id, tenant_id=tenant_id,
                    domain_id=domain_id, group_id=group_id)
            except exception.MetadataNotFound:
                pass
        return metadata_ref

    def _get_group_metadata_ref(self, user_id, tenant_id=None, domain_id=None):
        """Return any metadata for this project/domain due to group grants."""
        group_refs = self.identity_api.list_groups_for_user(
            context=self.context, user_id=user_id)
        metadata_ref = {}
        for x in group_refs:
            metadata_ref.update(self._get_metadata_ref(group_id=x['id'],
                                                       tenant_id=tenant_id,
                                                       domain_id=domain_id))
        return metadata_ref

    def _append_roles(self, metadata, additional_metadata):
        """Update the roles in metadata to be the union of the roles
        from both of the passed metadatas
        """

        first = set(metadata.get('roles', []))
        second = set(additional_metadata.get('roles', []))
        metadata['roles'] = list(first.union(second))

    def _get_project_roles_for_user(self, user_id, project_id):
        #FIXME(gyee) get_roles_for_user_and_project is supposed to return
        # all the roles assigned to the user for the project, including
        # assignment via group membership. Unfortunately, not all backends
        # does this correctly. For now, lets do this explicitly.
        #roles = self.identity_api.get_roles_for_user_and_project(
        #    self.context, user_id, project_id)
        metadata_ref = self._get_metadata_ref(user_id, project_id)
        self._append_roles(metadata_ref,
                           self._get_group_metadata_ref(user_id, project_id))
        roles_ref = []
        for role_id in metadata_ref.get('roles', []):
            role_ref = self.identity_api.get_role(self.context, role_id)
            role_ref.setdefault('project_id', project_id)
            roles_ref.append(role_ref)
        # user have no project roles, therefore access denied
        if not roles_ref:
            msg = _('User have no access to project')
            LOG.debug(msg)
            raise exception.Unauthorized(msg)
        return roles_ref

    def _get_domain_roles_for_user(self, user_id, domain_id):
        #FIXME(gyee) get_roles_for_user_and_project is supposed to return
        # all the roles assigned to the user for the project, including
        # assignment via group membership. Unfortunately, not all backends
        # does this correctly. For now, lets do this explicitly.
        #roles = self.identity_api.get_roles_for_user_and_domain(
        #    self.context, user_id, domain_id)
        metadata_ref = self._get_metadata_ref(user_id, domain_id=domain_id)
        self._append_roles(metadata_ref,
                           self._get_group_metadata_ref(
                               user_id, domain_id=domain_id))
        roles_ref = []
        for role_id in metadata_ref.get('roles', []):
            role_ref = self.identity_api.get_role(self.context, role_id)
            role_ref.setdefault('domain_id', domain_id)
            roles_ref.append(role_ref)
        # user have no domain roles, therefore access denied
        if not roles_ref:
            msg = _('User have no access to domain')
            LOG.debug(msg)
            raise exception.Unauthorized(msg)
        return roles_ref

    def _get_roles_for_user(self, user_id, domain_id, project_id,
                            metadata_ref):
        roles = []
        if metadata_ref and 'roles' in metadata_ref:
            # FIXME(gyee): for V2, roles come from metadata?
            for role_id in metadata_ref.get('roles', []):
                role_ref = self.identity_api.get_role(self.context, role_id)
                roles.append({
                    'id': role_ref['id'],
                    'name': role_ref['name']})
            if project_id and not roles:
                msg = _('User have no access to tenant')
                LOG.debug(msg)
                raise exception.Unauthorized(msg)
        else:
            if domain_id:
                roles = self._get_domain_roles_for_user(user_id, domain_id)
            if project_id:
                roles = self._get_project_roles_for_user(user_id, project_id)
        return roles

    def _to_boolean(self, obj):
        if isinstance(obj, basestring):
            return obj.lower() in ('true', 't', '1')
        else:
            return obj

    def _populate_user(self, token_data, user_id, domain_id, project_id,
                       trust):
        user_ref = self.identity_api.get_user(self.context,
                                              user_id)
        if CONF.trust.enabled and trust:
            trust = self.trust_api.get_trust(self.context, trust['id'])
            trustor_user_ref = (self.identity_api.get_user(self.context,
                                trust['trustor_user_id']))
            if not trustor_user_ref['enabled']:
                raise exception.Forbidden()
            if self._to_boolean(trust['impersonation']):
                user_ref = trustor_user_ref
            token_data['OS-TRUST:trust'] = (
                {
                    'id': trust['id'],
                    'trustor_user': {'id': trust['trustor_user_id']},
                    'trustee_user': {'id': trust['trustee_user_id']},
                    'impersonation': trust['impersonation']
                })
        filtered_user = {
            'id': user_ref['id'],
            'name': user_ref['name'],
            'domain': self._get_filtered_domain(user_ref['domain_id'])}
        token_data['user'] = filtered_user

    def _populate_roles(self, token_data, user_id, domain_id, project_id,
                        metadata_ref, trust):
        if CONF.trust.enabled and trust:
            token_user_id = trust['trustor_user_id']
            token_project_id = trust['project_id']
            #trusts do not support domains yet
            token_domain_id = None
        else:
            token_user_id = user_id
            token_project_id = project_id
            token_domain_id = domain_id

        if token_domain_id or token_project_id:
            roles = self._get_roles_for_user(token_user_id,
                                             token_domain_id,
                                             token_project_id,
                                             metadata_ref)
            filtered_roles = []
            if CONF.trust.enabled and trust:
                for trust_role in trust['roles']:
                    match_roles = [x for x in roles
                                   if x['id'] == trust_role['id']]
                    if match_roles:
                        filtered_roles.append(match_roles[0])
                    else:
                        raise exception.Forbidden()
            else:
                for role in roles:
                    filtered_roles.append({'id': role['id'],
                                           'name': role['name']})
            token_data['roles'] = filtered_roles

    def _get_catalog(self, user_id, project_id):
        catalog_ref = self.catalog_api.get_catalog(
            context=self.context,
            user_id=user_id,
            tenant_id=project_id)
        if not catalog_ref:
            return []
        services = {}
        for region, region_ref in catalog_ref.iteritems():
            for service, service_ref in region_ref.iteritems():
                new_service_ref = services.get(service, {})
                new_service_ref.setdefault('id', service_ref['id'])
                new_service_ref.setdefault('type', service)
                new_service_ref.setdefault('name', service_ref['name'])
                if 'endpoints' not in new_service_ref:
                    new_service_ref['endpoints'] = []
                for attr in service_ref.keys():
                    if attr.endswith('URL'):
                        interface = attr[:-3]
                        new_service_ref['endpoints'].append({
                            'interface': interface,
                            'url': service_ref[attr],
                            'region': region,
                            'id': service_ref['id']})
                services[service] = new_service_ref
        return services.values()

    def _populate_service_catalog(self, token_data, user_id,
                                  domain_id, project_id, trust):
        if CONF.trust.enabled and trust:
            user_id = trust['trustor_user_id']
        if project_id or domain_id:
            try:
                service_catalog = self.catalog_api.get_v3_catalog(
                    self.context, user_id, project_id)
            except exception.NotImplemented:
                # for backends which doesn't provide v3 catalog, lets do
                # this the old way
                try:
                    service_catalog = self._get_catalog(user_id, project_id)
                except Exception as e:
                    # not much we can do here
                    LOG.exception(e)
                    service_catalog = {}
            #TODO(gyee): v3 service catalog is not quite completed yet
            #TODO(ayoung): Enforce Endpoints for trust
            token_data['catalog'] = service_catalog

    def _populate_token(self, token_data, expires=None, trust=None):
        if not expires:
            expires = token.default_expire_time()
        if not isinstance(expires, basestring):
            expires = timeutils.isotime(expires, subsecond=True)
        token_data['expires_at'] = expires
        token_data['issued_at'] = timeutils.isotime(subsecond=True)

    def _populate_metadata(self, token_data, metadata_ref):
        if metadata_ref:
            if 'is_admin' in metadata_ref:
                token_data['metadata'] = {'is_admin': metadata_ref['is_admin']}
            else:
                token_data['metadata'] = {'is_admin': '0'}
            # FIXME(gyee): why are we stashing roles in metadata_ref?
            if 'roles' in metadata_ref:
                token_data['metadata']['roles'] = metadata_ref['roles']

    def get_token_data(self, user_id, method_names, extras,
                       domain_id=None, project_id=None, expires=None,
                       metadata_ref=None, trust=None, need_catalog=True):
        token_data = {'methods': method_names,
                      'extras': extras}

        if CONF.trust.enabled and trust:
            if user_id != trust['trustee_user_id']:
                raise exception.Forbidden()
        self._populate_scope(token_data, domain_id, project_id)
        self._populate_user(token_data, user_id, domain_id, project_id, trust)
        self._populate_metadata(token_data, metadata_ref)
        self._populate_roles(token_data, user_id, domain_id, project_id,
                             metadata_ref, trust)
        self._populate_service_catalog(token_data, user_id, domain_id,
                                       project_id, trust)
        self._populate_token(token_data, expires, trust)
        return {'token': token_data}


@dependency.requires('token_api', 'identity_api')
class Provider(token_provider.Driver):
    def __init__(self, *args, **kwargs):
        super(Provider, self).__init__(*args, **kwargs)
        if CONF.trust.enabled:
            self.trust_api = trust.Manager()

    def get_token_version(self, token_data):
        if token_data and isinstance(token_data, dict):
            if 'access' in token_data:
                return token_provider.V2
            if 'token' in token_data and 'methods' in token_data['token']:
                return token_provider.V3
        raise token_provider.UnsupportedTokenVersionException()

    def _get_token_id(self, token_data):
        # TODO(gyee): would it be nice if we can tell the token version from
        # the token_id?
        if CONF.signing.token_format == 'UUID':
            token_id = uuid.uuid4().hex
        elif CONF.signing.token_format == 'PKI':
            try:
                token_id = cms.cms_sign_token(json.dumps(token_data),
                                              CONF.signing.certfile,
                                              CONF.signing.keyfile)
            except environment.subprocess.CalledProcessError:
                raise exception.UnexpectedError(_(
                    'Unable to sign token.'))
        else:
            raise exception.UnexpectedError(_(
                'Invalid value for token_format: %s.'
                '  Allowed values are PKI or UUID.') %
                CONF.signing.token_format)
        return token_id

    def _issue_v3_token(self, user_id, method_names,
                        expires_at=None,
                        project_id=None, domain_id=None,
                        auth_context=None, **kwargs):
        token_data_helper = V3TokenDataHelper(None)
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
                metadata_ref.setdefault('trustee_user_id',
                                        trust['trustee_user_id'])
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
            LOG.exception(_('Failed to issue V3 token'))
            # an identical token may have been created already.
            # if so, return the token_data as it is also identical
            try:
                self.token_api.get_token(None,
                                         token_id=token_id)
            except exception.TokenNotFound:
                raise e

        return (token_id, token_data)

    def issue_token(self, user_id, method_names, version='v3.0',
                    expires_at=None,
                    project_id=None, domain_id=None,
                    auth_context=None, **kwargs):
        if version == token_provider.V3:
            return self._issue_v3_token(user_id, method_names,
                                        expires_at=expires_at,
                                        project_id=project_id,
                                        domain_id=domain_id,
                                        auth_context=auth_context,
                                        **kwargs)
        raise token_provider.UnsupportedTokenVersionException

    def _verify_token(self, token_id, belongs_to=None):
        """Verify the given token and return the token_ref."""
        token_ref = self.token_api.get_token(None,
                                             token_id=token_id)
        assert token_ref
        if belongs_to:
            assert token_ref['tenant']['id'] == belongs_to
        return token_ref

    def revoke_token(self, token_id):
        self.token_api.delete_token(None, token_id=token_id)

    def _validate_v3_token(self, token_id, belongs_to=None, **kwargs):
        try:
            token_ref = self._verify_token(token_id, belongs_to)
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
                token_data_helper = V3TokenDataHelper(None)
                token_data = token_data_helper.get_token_data(
                    user_id=token_ref['user']['id'],
                    method_names=['password', 'token'],
                    extras={},
                    domain_id=None,
                    project_id=project_id,
                    expires=token_ref['expires'],
                    trust=None)
            return token_data
        except Exception as e:
            LOG.exception(_('Failed to validate token'))
            raise exception.Unauthorized(e)

    def validate_token(self, token_id, belongs_to=None, version='v3.0',
                       **kwargs):
        if version == token_provider.V3:
            return self._validate_v3_token(token_id,
                                           belongs_to=belongs_to,
                                           **kwargs)
        raise token_provider.UnsupportedTokenVersionException

    def check_token(self, token_id, belongs_to=None, **kwargs):
        try:
            self._verify_token(token_id, belongs_to)
        except Exception as e:
            LOG.exception(_('Failed to verify token'))
            raise exception.Unauthorized(e)
