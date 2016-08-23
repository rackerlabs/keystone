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

from oslo_log import log
from oslo_serialization import msgpackutils
from oslo_utils import timeutils

from keystone.common import cache
from keystone.common import utils


LOG = log.getLogger(__name__)

# The set of attributes common between the RevokeEvent
# and the dictionaries created from the token Data.
_NAMES = ['trust_id',
          'consumer_id',
          'access_token_id',
          'audit_id',
          'audit_chain_id',
          'expires_at',
          'domain_id',
          'project_id',
          'user_id',
          'role_id']


# Additional arguments for creating a RevokeEvent
_EVENT_ARGS = ['issued_before', 'revoked_at']

# Names of attributes in the RevocationEvent, including "virtual" attributes.
# Virtual attributes are those added based on other values.
_EVENT_NAMES = _NAMES + ['domain_scope_id']

# Values that will be in the token data but not in the event.
# These will compared with event values that have different names.
# For example: both trustor_id and trustee_id are compared against user_id
_TOKEN_KEYS = ['identity_domain_id',
               'assignment_domain_id',
               'issued_at',
               'trustor_id',
               'trustee_id']

# Alternative names to be checked in token for every field in
# revoke tree.
ALTERNATIVES = {
    'user_id': ['user_id', 'trustor_id', 'trustee_id'],
    'domain_id': ['identity_domain_id', 'assignment_domain_id'],
    # For a domain-scoped token, the domain is in assignment_domain_id.
    'domain_scope_id': ['assignment_domain_id', ],
}


REVOKE_KEYS = _NAMES + _EVENT_ARGS


def blank_token_data(issued_at):
    token_data = dict()
    for name in _NAMES:
        token_data[name] = None
    for name in _TOKEN_KEYS:
        token_data[name] = None
    # required field
    token_data['issued_at'] = issued_at
    return token_data


class RevokeEvent(object):
    def __init__(self, **kwargs):
        for k in REVOKE_KEYS:
            v = kwargs.get(k)
            setattr(self, k, v)

        if self.domain_id and self.expires_at:
            # This is revoking a domain-scoped token.
            self.domain_scope_id = self.domain_id
            self.domain_id = None
        else:
            # This is revoking all tokens for a domain.
            self.domain_scope_id = None

        if self.expires_at is not None:
            # Trim off the expiration time because MySQL timestamps are only
            # accurate to the second.
            self.expires_at = self.expires_at.replace(microsecond=0)

        if self.revoked_at is None:
            self.revoked_at = timeutils.utcnow().replace(microsecond=0)
        if self.issued_before is None:
            self.issued_before = self.revoked_at

    def to_dict(self):
        keys = ['user_id',
                'role_id',
                'domain_id',
                'domain_scope_id',
                'project_id',
                'audit_id',
                'audit_chain_id',
                ]
        event = {key: self.__dict__[key] for key in keys
                 if self.__dict__[key] is not None}
        if self.trust_id is not None:
            event['OS-TRUST:trust_id'] = self.trust_id
        if self.consumer_id is not None:
            event['OS-OAUTH1:consumer_id'] = self.consumer_id
        if self.access_token_id is not None:
            event['OS-OAUTH1:access_token_id'] = self.access_token_id
        if self.expires_at is not None:
            event['expires_at'] = utils.isotime(self.expires_at)
        if self.issued_before is not None:
            event['issued_before'] = utils.isotime(self.issued_before,
                                                   subsecond=True)
        if self.revoked_at is not None:
            event['revoked_at'] = utils.isotime(self.revoked_at,
                                                subsecond=True)
        return event


def build_token_values_v2(access, default_domain_id):
    token_data = access['token']

    token_expires_at = timeutils.parse_isotime(token_data['expires'])

    # Trim off the microseconds because the revocation event only has
    # expirations accurate to the second.
    token_expires_at = token_expires_at.replace(microsecond=0)

    token_values = {
        'expires_at': timeutils.normalize_time(token_expires_at),
        'issued_at': timeutils.normalize_time(
            timeutils.parse_isotime(token_data['issued_at'])),
        'audit_id': token_data.get('audit_ids', [None])[0],
        'audit_chain_id': token_data.get('audit_ids', [None])[-1],
    }

    token_values['user_id'] = access.get('user', {}).get('id')

    project = token_data.get('tenant')
    if project is not None:
        token_values['project_id'] = project['id']
    else:
        token_values['project_id'] = None

    token_values['identity_domain_id'] = default_domain_id
    token_values['assignment_domain_id'] = default_domain_id

    trust = access.get('trust')
    if trust is None:
        token_values['trust_id'] = None
        token_values['trustor_id'] = None
        token_values['trustee_id'] = None
    else:
        token_values['trust_id'] = trust['id']
        token_values['trustor_id'] = trust['trustor_user_id']
        token_values['trustee_id'] = trust['trustee_user_id']

    token_values['consumer_id'] = None
    token_values['access_token_id'] = None

    role_list = []
    # Roles are by ID in metadata and by name in the user section
    roles = access.get('metadata', {}).get('roles', [])
    for role in roles:
        role_list.append(role)
    token_values['roles'] = role_list
    return token_values


def build_token_values(token_data):

    token_expires_at = timeutils.parse_isotime(token_data['expires_at'])

    # Trim off the microseconds because the revocation event only has
    # expirations accurate to the second.
    token_expires_at = token_expires_at.replace(microsecond=0)

    token_values = {
        'expires_at': timeutils.normalize_time(token_expires_at),
        'issued_at': timeutils.normalize_time(
            timeutils.parse_isotime(token_data['issued_at'])),
        'audit_id': token_data.get('audit_ids', [None])[0],
        'audit_chain_id': token_data.get('audit_ids', [None])[-1],
    }

    user = token_data.get('user')
    if user is not None:
        token_values['user_id'] = user['id']
        # Federated users do not have a domain, be defensive and get the user
        # domain set to None in the federated user case.
        token_values['identity_domain_id'] = user.get('domain', {}).get('id')
    else:
        token_values['user_id'] = None
        token_values['identity_domain_id'] = None

    project = token_data.get('project', token_data.get('tenant'))
    if project is not None:
        token_values['project_id'] = project['id']
        # The domain_id of projects acting as domains is None
        token_values['assignment_domain_id'] = (
            project['domain']['id'] if project['domain'] else None)
    else:
        token_values['project_id'] = None

        domain = token_data.get('domain')
        if domain is not None:
            token_values['assignment_domain_id'] = domain['id']
        else:
            token_values['assignment_domain_id'] = None

    role_list = []
    roles = token_data.get('roles')
    if roles is not None:
        for role in roles:
            role_list.append(role['id'])
    token_values['roles'] = role_list

    trust = token_data.get('OS-TRUST:trust')
    if trust is None:
        token_values['trust_id'] = None
        token_values['trustor_id'] = None
        token_values['trustee_id'] = None
    else:
        token_values['trust_id'] = trust['id']
        token_values['trustor_id'] = trust['trustor_user']['id']
        token_values['trustee_id'] = trust['trustee_user']['id']

    oauth1 = token_data.get('OS-OAUTH1')
    if oauth1 is None:
        token_values['consumer_id'] = None
        token_values['access_token_id'] = None
    else:
        token_values['consumer_id'] = oauth1['consumer_id']
        token_values['access_token_id'] = oauth1['access_token_id']
    return token_values


class _RevokeEventHandler(object):
    # NOTE(morganfainberg): There needs to be reserved "registry" entries set
    # in oslo_serialization for application-specific handlers. We picked 127
    # here since it's waaaaaay far out before oslo_serialization will use it.
    identity = 127
    handles = (RevokeEvent,)

    def __init__(self, registry):
        self._registry = registry

    def serialize(self, obj):
        return msgpackutils.dumps(obj.__dict__, registry=self._registry)

    def deserialize(self, data):
        revoke_event_data = msgpackutils.loads(data, registry=self._registry)
        try:
            revoke_event = RevokeEvent(**revoke_event_data)
        except Exception:
            LOG.debug("Failed to deserialize RevokeEvent. Data is %s",
                      revoke_event_data)
            raise
        return revoke_event


cache.register_model_handler(_RevokeEventHandler)
