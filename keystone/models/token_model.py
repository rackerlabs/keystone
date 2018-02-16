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

"""Unified in-memory token model."""

import base64
import datetime
import itertools
import uuid

from oslo_utils import reflection
from oslo_utils import timeutils
import six

from keystone.common import provider_api
from keystone.common import utils
import keystone.conf
from keystone import exception
from keystone.federation import constants
from keystone.i18n import _

# supported token versions
V3 = 'v3.0'
VERSIONS = frozenset([V3])
CONF = keystone.conf.CONF
PROVIDERS = provider_api.ProviderAPIs


def default_expire_time():
    """Determine when a fresh token should expire.

    Expiration time varies based on configuration (see ``[token] expiration``).

    :returns: a naive UTC datetime.datetime object

    """
    expire_delta = datetime.timedelta(seconds=CONF.token.expiration)
    expires_at = timeutils.utcnow() + expire_delta
    return expires_at.replace(microsecond=0)


def random_urlsafe_str():
    """Generate a random URL-safe string.

    :rtype: six.text_type

    """
    # chop the padding (==) off the end of the encoding to save space
    return base64.urlsafe_b64encode(uuid.uuid4().bytes)[:-2].decode('utf-8')


def _parse_and_normalize_time(time_data):
    if isinstance(time_data, six.string_types):
        time_data = timeutils.parse_isotime(time_data)
    return timeutils.normalize_time(time_data)


class KeystoneToken(dict):
    """An in-memory representation that unifies v3 tokens."""

    # TODO(morganfainberg): Align this in-memory representation with the
    # objects in keystoneclient. This object should be eventually updated
    # to be the source of token data with the ability to emit any version
    # of the token instead of only consuming the token dict and providing
    # property accessors for the underlying data.

    def __init__(self, token_id, token_data):
        self.token_data = token_data
        self.token_id = token_id
        try:
            super(KeystoneToken, self).__init__(**token_data['token'])
        except KeyError:
            raise exception.UnsupportedTokenVersionException()

        if self.project_scoped and self.domain_scoped:
            raise exception.UnexpectedError(_('Found invalid token: scoped to '
                                              'both project and domain.'))

    def __repr__(self):
        """Return string representation of KeystoneToken."""
        desc = ('<%(type)s (audit_id=%(audit_id)s, '
                'audit_chain_id=%(audit_chain_id)s) at %(loc)s>')
        self_cls_name = reflection.get_class_name(self,
                                                  fully_qualified=False)
        return desc % {'type': self_cls_name,
                       'audit_id': self.audit_id,
                       'audit_chain_id': self.audit_chain_id,
                       'loc': hex(id(self))}

    @property
    def expires(self):
        return _parse_and_normalize_time(self['expires_at'])

    @property
    def issued(self):
        return _parse_and_normalize_time(self['issued_at'])

    @property
    def audit_id(self):
        return self.get('audit_ids', [None])[0]

    @property
    def audit_chain_id(self):
        return self.get('audit_ids', [None])[-1]

    @property
    def auth_token(self):
        return self.token_id

    @property
    def user_id(self):
        return self['user']['id']

    @property
    def user_name(self):
        return self['user']['name']

    @property
    def user_domain_name(self):
        try:
            return self['user']['domain']['name']
        except KeyError:  # nosec
            # Do not raise KeyError, raise UnexpectedError
            pass
        raise exception.UnexpectedError()

    @property
    def user_password_expires_at(self):
        try:
            return self['user']['password_expires_at']
        except KeyError:
            # Do not raise KeyError, raise UnexpectedError
            pass
        raise exception.UnexpectedError()

    @property
    def user_domain_id(self):
        try:
            return self['user']['domain']['id']
        except KeyError:  # nosec
            # Do not raise KeyError, raise UnexpectedError
            pass
        raise exception.UnexpectedError()

    @property
    def domain_id(self):
        try:
            return self['domain']['id']
        except KeyError:
            # Do not raise KeyError, raise UnexpectedError
            raise exception.UnexpectedError()

    @property
    def domain_name(self):
        try:
            return self['domain']['name']
        except KeyError:
            # Do not raise KeyError, raise UnexpectedError
            raise exception.UnexpectedError()

    @property
    def project_id(self):
        try:
            return self['project']['id']
        except KeyError:
            # Do not raise KeyError, raise UnexpectedError
            raise exception.UnexpectedError()

    @property
    def project_name(self):
        try:
            return self['project']['name']
        except KeyError:
            # Do not raise KeyError, raise UnexpectedError
            raise exception.UnexpectedError()

    @property
    def project_domain_id(self):
        try:
            return self['project']['domain']['id']
        except KeyError:  # nosec
            # Do not raise KeyError, raise UnexpectedError
            pass

        raise exception.UnexpectedError()

    @property
    def project_domain_name(self):
        try:
            return self['project']['domain']['name']
        except KeyError:  # nosec
            # Do not raise KeyError, raise UnexpectedError
            pass

        raise exception.UnexpectedError()

    @property
    def is_domain(self):
        if 'is_domain' in self:
            return self['is_domain']
        return False

    @property
    def system_scoped(self):
        return 'system' in self

    @property
    def project_scoped(self):
        return 'project' in self

    @property
    def domain_scoped(self):
        return 'domain' in self

    @property
    def scoped(self):
        return self.project_scoped or self.domain_scoped or self.system_scoped

    @property
    def is_admin_project(self):
        # Prevent domain scoped tokens from acting as is_admin_project
        if self.domain_scoped:
            return False
        # TODO(ayoung/edmondsw): Having is_admin_project default to True is
        # essential for fixing bug #968696. If an admin project is not
        # configured, we can add checks for is_admin_project:True and not
        # block anyone that hasn't configured an admin_project. Do not change
        # this until we can assume admin_project is actually set
        return self.get('is_admin_project', True)

    @property
    def trust_id(self):
        return self.get('OS-TRUST:trust', {}).get('id')

    @property
    def trust_scoped(self):
        return 'OS-TRUST:trust' in self

    @property
    def trustee_user_id(self):
        return self.get('OS-TRUST:trust', {}).get('trustee_user_id')

    @property
    def trustor_user_id(self):
        return self.get('OS-TRUST:trust', {}).get('trustor_user_id')

    @property
    def trust_impersonation(self):
        return self.get('OS-TRUST:trust', {}).get('impersonation')

    @property
    def oauth_scoped(self):
        return 'OS-OAUTH1' in self

    @property
    def oauth_access_token_id(self):
        if self.oauth_scoped:
            return self['OS-OAUTH1']['access_token_id']
        return None

    @property
    def oauth_consumer_id(self):
        if self.oauth_scoped:
            return self['OS-OAUTH1']['consumer_id']
        return None

    @property
    def role_ids(self):
        return [r['id'] for r in self.get('roles', [])]

    @property
    def role_names(self):
        return [r['name'] for r in self.get('roles', [])]

    @property
    def bind(self):
        return self.get('bind')

    @property
    def is_federated_user(self):
        try:
            return constants.FEDERATION in self['user']
        except KeyError:
            raise exception.UnexpectedError()

    @property
    def federation_group_ids(self):
        if self.is_federated_user:
            try:
                groups = self['user'][constants.FEDERATION].get('groups', [])
                return [g['id'] for g in groups]
            except KeyError:
                raise exception.UnexpectedError()
        return []

    @property
    def federation_idp_id(self):
        if self.is_federated_user:
            return (
                self['user'][constants.FEDERATION]['identity_provider']['id']
            )

    @property
    def federation_protocol_id(self):
        if self.is_federated_user:
            return self['user'][constants.FEDERATION]['protocol']['id']
        return None

    @property
    def metadata(self):
        return self.get('metadata', {})

    @property
    def methods(self):
        return self.get('methods', [])


class TokenModel(object):

    def __init__(self, user_id, methods, expires_at=None, system=None,
                 domain_id=None, project_id=None, auth_context=None,
                 trust_id=None, app_cred_id=None, parent_audit_id=None):
        self.methods = methods
        self.expires_at = expires_at
        self.issued_at = None
        self.system = system
        self.domain_id = domain_id
        self.project_id = project_id
        self.auth_context = auth_context
        self.trust_id = trust_id
        self.application_credential_id = app_cred_id
        self.audit_id = random_urlsafe_str()
        self.parent_audit_id = parent_audit_id

        if 'oauth1' in methods:
            self.access_token_id = self.auth_context['access_token_id']
        else:
            self.access_token_id = None

        if self.is_federated:
            self.user_id = self.auth_context['user_id']
        else:
            self.user_id = user_id

        if not self.expires_at:
            self.expires_at = utils.isotime(
                default_expire_time(), subsecond=True
            )

    def __repr__(self):
        """Return string representation of KeystoneToken."""
        desc = ('<%(type)s (audit_id=%(audit_id)s, '
                'audit_chain_id=%(audit_ids)s) at %(loc)s>')
        self_cls_name = reflection.get_class_name(self, fully_qualified=False)
        return desc % {'type': self_cls_name,
                       'audit_id': self.audit_id,
                       'audit_ids': self.audit_ids,
                       'loc': hex(id(self))}

    @property
    def audit_ids(self):
        if self.parent_audit_id:
            return [self.audit_id, self.parent_audit_id]
        return [self.audit_id]

    @property
    def system_scoped(self):
        return self.system is not None

    @property
    def domain(self):
        if self.domain_id:
            return PROVIDERS.resource_api.get_domain(self.domain_id)

    @property
    def domain_scoped(self):
        return self.domain_id is not None

    @property
    def project(self):
        if self.project_id:
            return PROVIDERS.resource_api.get_project(self.project_id)

    @property
    def project_scoped(self):
        return self.project_id is not None

    @property
    def project_domain(self):
        if self.project and self.project.get('domain_id'):
            return PROVIDERS.resource_api.get_domain(self.project['domain_id'])

    @property
    def application_credential(self):
        if self.application_credential_id:
            app_cred_api = PROVIDERS.application_credential_api
            return app_cred_api.get_application_credential(
                self.application_credential_id
            )

    @property
    def access_token(self):
        if self.access_token_id:
            return PROVIDERS.oauth_api.get_access_token(self.access_token_id)

    @property
    def trust(self):
        if self.trust_id:
            return PROVIDERS.trust_api.get_trust(self.trust_id)

    @property
    def trust_scoped(self):
        return self.trust_id is not None

    @property
    def trustor(self):
        if self.trust:
            return PROVIDERS.identity_api.get_user(
                self.trust['trustor_user_id']
            )

    @property
    def trustee(self):
        if self.trust:
            return PROVIDERS.identity_api.get_user(
                self.trust['trustee_user_id']
            )

    @property
    def user(self):
        return PROVIDERS.identity_api.get_user(self.user_id)

    @property
    def username(self):
        return self.user['name']

    @property
    def user_domain(self):
        if self.trust_scoped:
            return PROVIDERS.resource_api.get_domain(self.trustor['domain_id'])
        else:
            return PROVIDERS.resource_api.get_domain(self.user['domain_id'])

    @property
    def groups(self):
        if self.is_federated:
            return [{'id': group} for group in self.auth_context['group_ids']]
        else:
            return PROVIDERS.identity_api.list_groups_for_user(self.user_id)

    @property
    def identity_provider(self):
        if self.is_federated:
            return self.auth_context[constants.IDENTITY_PROVIDER]

    @property
    def protocol(self):
        if self.is_federated:
            return self.auth_context[constants.PROTOCOL]

    @property
    def is_federated(self):
        return (constants.IDENTITY_PROVIDER in self.auth_context and
                constants.PROTOCOL in self.auth_context)

    @property
    def roles(self):
        roles = []
        if self.system_scoped:
            groups = PROVIDERS.identity_api.list_groups_for_user(self.user_id)
            group_roles = []
            for group in groups:
                roles = PROVIDERS.assignment_api.list_system_grants_for_group(
                    group['id']
                )
                for role in roles:
                    group_roles.append(role)
            user_roles = PROVIDERS.assignment_api.list_system_grants_for_user(
                self.user_id
            )
            for role in itertools.chain(group_roles, user_roles):
                roles.append({'id': role['id'], 'name': role['name']})
        elif self.trust_scoped:
            # If redelegated_trust_id is set, then we must traverse the
            # trust_chain in order to determine who the original trustor is. We
            # need to do this because the user ID of the original trustor helps
            # us determine scope in the redelegated context.
            if self.trust.get('redelegated_trust_id'):
                trust_chain = PROVIDERS.trust_api.get_trust_pedigree(
                    self.trust_id
                )
                original_trustor_id = trust_chain[-1]['trustor_user_id']
            else:
                original_trustor_id = self.trustor['id']

            trustor_assignments = (
                PROVIDERS.assignment_api.list_role_assignments(
                    user_id=original_trustor_id,
                    project_id=self.trust.get('project_id'),
                    effective=True, strip_domain_roles=False
                )
            )
            for a in trustor_assignments:
                role = PROVIDERS.role_api.get_role(a['role_id'])
                roles.append({'id': role['id'], 'name': role['name']})
        elif self.domain_scoped:
            domain_roles = (
                PROVIDERS.assignment_api.get_roles_for_user_and_domain(
                    self.user_id, self.domain_id
                )
            )
            for role in domain_roles:
                roles.append({'id': role['id'], 'name': role['name']})
        elif self.project_scoped:
            project_roles = (
                PROVIDERS.assignment_api.get_roles_for_user_and_project(
                    self.user_id, self.project_id
                )
            )
            for role_id in project_roles:
                r = PROVIDERS.role_api.get_role(role_id)
                roles.append({'id': r['id'], 'name': r['name']})
        elif self.application_credential_id:
            app_cred_roles = self.application_credential['roles']
            for role in app_cred_roles:
                try:
                    r = PROVIDERS.assignment_api.get_grant(
                        role['id'], user_id=self.user_id,
                        domain_id=self.domain_id, project_id=self.project_id)
                    roles.append({'id': r['id'], 'name': r['name']})
                except exception.RoleAssignmentNotFound:
                    pass
        return roles
