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

from oslo_utils import timeutils
from six.moves import map

from keystone.common import utils


# The set of attributes common between the RevokeEvent
# and the dictionaries created from the token Data.
_NAMES = ['audit_id',
          'audit_chain_id',
          'expires_at',
          'user_id']


# Additional arguments for creating a RevokeEvent
_EVENT_ARGS = ['issued_before', 'revoked_at']

# Names of attributes in the RevocationEvent, including "virtual" attributes.
# Virtual attributes are those added based on other values.
_EVENT_NAMES = _NAMES

# Values that will be in the token data but not in the event.
# These will compared with event values that have different names.
_TOKEN_KEYS = ['issued_at', 'trustee_id']

# Alternative names to be checked in token for every field in
# revoke tree.
ALTERNATIVES = {
    'user_id': ['user_id', 'trustee_id'],
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
        if self.expires_at is not None:
            # Trim off the expiration time because MySQL timestamps are only
            # accurate to the second.
            self.expires_at = self.expires_at.replace(microsecond=0)
        if self.revoked_at is None:
            self.revoked_at = timeutils.utcnow()
        if self.issued_before is None:
            self.issued_before = self.revoked_at

    def to_dict(self):
        keys = ['user_id',
                'audit_id',
                'audit_chain_id',
                ]
        event = {key: self.__dict__[key] for key in keys
                 if self.__dict__[key] is not None}
        if self.expires_at is not None:
            event['expires_at'] = utils.isotime(self.expires_at)
        if self.issued_before is not None:
            event['issued_before'] = utils.isotime(self.issued_before,
                                                   subsecond=True)
        return event

    def key_for_name(self, name):
        return "%s=%s" % (name, getattr(self, name) or '*')


def attr_keys(event):
    return list(map(event.key_for_name, _EVENT_NAMES))


def is_revoked(events, token_data):
    """Check if a token matches a revocation event.

    Compare a token against every revocation event. If the token matches an
    event in the `events` list, the token is revoked. If the token is compared
    against every item in the list without a match, it is not considered
    revoked from the `revoke_api`.

    :param events: a list data structure of events
    :param token_data: map based on a flattened view of the token. The required
                       fields are `expires_at`,`user_id`, 'audit_id', and
                                   'audit_chain_id'
    :returns: True if the token matches an existing revocation event, meaning
              the token is revoked. False is returned if the token does not
              match any revocation events, meaning the token is considered
              valid by the revocation API.
    """
    return any([matches(e, token_data) for e in events])


def matches(event, token_values):
    """See if the token matches the revocation event.

    A brute force approach to checking.
    Compare each attribute from the event with the corresponding
    value from the token.  If the event does not have a value for
    the attribute, a match is still possible.  If the event has a
    value for the attribute, and it does not match the token, no match
    is possible, so skip the remaining checks.

    :param event: one revocation event to match
    :param token_values: dictionary with set of values taken from the
    token
    :returns: True if the token matches the revocation event, indicating the
    token has been revoked
    """
    # If any one check does not match, the whole token does
    # not match the event. The numerous return False indicate
    # that the token is still valid and short-circuits the
    # rest of the logic.

    # The token has three attributes that can match the user_id
    if event.user_id is not None:
        if all(event.user_id != token_values[attribute_name]
               for attribute_name in ['user_id', 'trustee_id']):
            return False

    # If an event specifies an attribute name, but it does not  match,
    # the token is not revoked.
    attribute_names = ['audit_id', 'audit_chain_id']
    for attribute_name in attribute_names:
        if getattr(event, attribute_name) is not None:
            if (getattr(event, attribute_name) !=
                    token_values[attribute_name]):
                        return False

    if token_values['issued_at'] > event.issued_before:
        return False
    return True


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

    trust = token_data.get('trust')
    if trust is None:
        token_values['trustee_id'] = None
    else:
        token_values['trustee_id'] = trust['trustee_id']

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
    else:
        token_values['user_id'] = None

    trust = token_data.get('OS-TRUST:trust')
    if trust is None:
        token_values['trustee_id'] = None
    else:
        token_values['trustee_id'] = trust['trustee_user']['id']

    return token_values
