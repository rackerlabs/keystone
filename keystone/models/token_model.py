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

from keystoneclient.common import cms
from oslo_utils import reflection
from oslo_utils import timeutils
import six

from keystone.common import dependency
import keystone.conf
from keystone import exception
from keystone.i18n import _

CONF = keystone.conf.CONF
# supported token versions
V2 = 'v2.0'
V3 = 'v3.0'
VERSIONS = frozenset([V2, V3])


def _parse_and_normalize_time(time_data):
    if isinstance(time_data, six.string_types):
        time_data = timeutils.parse_isotime(time_data)
    return timeutils.normalize_time(time_data)


@dependency.requires('assignment_api', 'identity_api', 'resource_api',
                     'trust_api')
class KeystoneToken(object):
    """An in-memory representation that unifies v2 and v3 tokens."""

    def __init__(self, token_id, user_id, methods, issued_at, expires_at,
                 audit_ids, domain_id=None, project_id=None, trust_id=None,
                 bind=None, access_token=None, is_federated=False,
                 federated_group_ids=None, federated_identity_provider=None,
                 federated_protocol_id=None):
        self.user_id = user_id
        self.methods = methods
        self.issued_at = issued_at
        self.expires_at = expires_at
        self.audit_ids = audit_ids
        self.domain_id = domain_id
        self.project_id = project_id
        self.trust_id = trust_id
        self.bind = bind
        self.access_token = access_token
        self.is_federated = is_federated
        self.federated_group_ids = federated_group_ids
        self.federated_identity_provider = federated_identity_provider
        self.federated_protocol_id = federated_protocol_id
        self.token_id = token_id
        self.short_id = cms.cms_hash_token(token_id,
                                           mode=CONF.token.hash_algorithm)

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
        return _parse_and_normalize_time(self.expires_at)

    @property
    def issued(self):
        return _parse_and_normalize_time(self.issued_at)

    @property
    def audit_id(self):
        return self.audit_ids[0]

    @property
    def audit_chain_id(self):
        return self.audit_ids[-1]

    @property
    def auth_token(self):
        return self.token_id

    @property
    def user_name(self):
        user = self.identity_api.get_user(self.user_id)
        return user['name']

    @property
    def user_domain_name(self):
        user = self.identity_api.get_user(self.user_id)
        return user['domain']['name']

    @property
    def user_domain_id(self):
        user = self.identity_api.get_user(self.user_id)
        return user.get('domain', {}).get('id')

    @property
    def domain_name(self):
        domain = self.resource_api.get_domain(self.domain_id)
        return domain['name']

    @property
    def project_name(self):
        project = self.resource_api.get_project(self.project_id)
        return project['name']

    @property
    def project_domain_id(self):
        project = self.resource_api.get_project(self.project_id)
        return project['domain']['id']

    @property
    def project_domain_name(self):
        project = self.resource_api.get_project(self.project_id)
        return project['domain']['name']

    @property
    def unscoped(self):
        return (
            not self.domain_scoped and not self.project_scoped and not
            self.oauth_scoped and not self.trust_scoped)

    @property
    def project_scoped(self):
        return self.project_id is not None

    @property
    def domain_scoped(self):
        return self.domain_id is not None

    @property
    def trust_scoped(self):
        return self.trust_id is not None

    @property
    def scoped(self):
        return self.project_scoped or self.domain_scoped or self.trust_scoped

    @property
    def trustee_user_id(self):
        if self.trust_id:
            trust = self.trust_api.get_trust(self.trust_id)
            return trust['trustee_user_id']

    @property
    def trustor_user_id(self):
        if self.trust_id:
            trust = self.trust_api.get_trust(self.trust_id)
            return trust['trustor_user_id']

    @property
    def trust_impersonation(self):
        if self.trust_id:
            trust = self.trust_api.get_trust(self.trust_id)
            return trust['impersonation']

    @property
    def oauth_scoped(self):
        return self.access_token is not None

    @property
    def oauth_access_token_id(self):
        if self.access_token:
            return self.access_token.get('access_token_id')

    @property
    def oauth_consumer_id(self):
        if self.access_token:
            return self.access_token.get('consumer_id')

    @property
    def role_ids(self):
        if self.project_id:
            return list(set(
                self.assignment_api.get_roles_for_user_and_project(
                    self.user_id, self.project_id
                )
            ))
        elif self.domain_id:
            return list(set(
                self.assignment_api.get_roles_for_user_and_domain(
                    self.user_id, self.domain_id
                )
            ))
        return []

    @property
    def role_names(self):
        role_names = []
        for role_id in self.role_ids:
            role_names.append(self.assignment_api.get_role(role_id)['name'])
        return role_names

    @property
    def is_federated_user(self):
        return self.is_federated

    @property
    def federation_group_ids(self):
        if self.federation_group_ids:
            return self.federated_group_ids
        return list()

    @property
    def federation_idp_id(self):
        return self.federated_identity_provider

    @property
    def federation_protocol_id(self):
        return self.federated_protocol_id
