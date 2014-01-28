# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
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


import uuid


from keystone.openstack.common import timeutils

#The set of attributes common between the RevokeEvent
#and the dictionaries created from the token Data.
_NAMES = ['trust_id',
          'consumer_id',
          'access_token_id',
          'expires_at',
          'domain_id',
          'project_id',
          'user_id',
          'role_id']


#additional arguments for creating a RevokeEvent
_EVENT_ARGS = ['id', 'issued_before', 'revoked_at']


_TOKEN_KEYS = ['user_domain_id',
               'project_domain_id',
               'issued_at',
               'trustor_id',
               'trustee_id']


REVOKE_KEYS = _NAMES + _EVENT_ARGS


def blank_token_data(issued_at):
    token_data = dict()
    for name in _NAMES:
        token_data[name] = None
    for name in _TOKEN_KEYS:
        token_data[name] = None
    #required field
    token_data['issued_at'] = issued_at
    return token_data


class RevokeEvent(object):
    def __init__(self, **kwargs):
        for k in REVOKE_KEYS:
            v = kwargs.get(k, None)
            setattr(self, k, v)
        if self.revoked_at is None:
            self.revoked_at = timeutils.utcnow()
        if self.issued_before is None:
            self.issued_before = self.revoked_at

    def to_dict(self):
        keys = ['user_id',
                'role_id',
                'domain_id',
                'project_id']
        event = dict((key, getattr(self, key)) for key in keys)
        event['id'] = str(self.id)
        if self.trust_id is not None:
            event['OS-TRUST:trust_id'] = self.trust_id
        if self.consumer_id is not None:
            event['OS-OAUTH1:consumer_id'] = self.consumer_id
        if self.consumer_id is not None:
            event['OS-OAUTH1:access_token_id'] = self.access_token_id
        if self.expires_at is not None:
            event['expires_at'] = timeutils.isotime(self.expires_at,
                                                    subsecond=True)
        if self.issued_before is not None:
            event['issued_before'] = timeutils.isotime(self.issued_before,
                                                       subsecond=True)
        return event

    def key_for_name(self, name):
        return "%s=%s" % (name, getattr(self, name) or '*')


class EventIdentifier(object):
    def __init__(self, value=None):
        self._value = value or uuid.uuid4()

    def __str__(self):
        return str(self._value)


def attr_keys(event):
    return map(event.key_for_name, _NAMES)


class RevokeTree(object):
    def __init__(self, revoke_events=[]):
        self.revoke_map = dict()
        self.add_events(revoke_events)

    def add_event(self, event):
        revoke_map = self.revoke_map
        for key in attr_keys(event):
            revoke_map = revoke_map.setdefault(key, {})
        revoke_map['issued_before'] = event.issued_before
        return event

    def remove_event(self, event):
        stack = []
        revoke_map = self.revoke_map
        for name in _NAMES:
            key = event.key_for_name(name)
            nxt = revoke_map.get(key)
            if nxt is None:
                break
            stack.append((revoke_map, key, nxt))
            revoke_map = nxt
        else:
            if event.issued_before == revoke_map['issued_before']:
                revoke_map.pop('issued_before')
        for parent, key, child in reversed(stack):
            if not any(child):
                del parent[key]

    def add_events(self, revoke_events):
        map(self.add_event, revoke_events)

    def is_revoked(self, token_data):

        #Compare each level of the tree with the values from the token,
        #taking into account the attributes that have alternative keys.
        #if there is a match, continue down the tree.
        #if there is no match, exit early.
        alternatives = {
            "user_id": ["user_id", "trustor_id", "trustee_id"],
            "domain_id": ["user_domain_id", "project_domain_id"]}
        subnode = [self.revoke_map]
        for name in _NAMES:
            bundle = []
            any_key = "%s=*" % (name,)
            for tree in subnode:
                bundle.append(tree.get(any_key))
                if name == "role_id":
                    for role_id in token_data.get("roles", []):
                        bundle.append(tree.get("role_id=%s" % (role_id,)))
                else:
                        for alt_name in alternatives.get(name, [name]):
                            bundle.append(
                                tree.get("%s=%s" % (name,
                                                    token_data[alt_name])))
                bundle = filter(None, bundle)
                if not bundle:
                    return False
                subnode = bundle
            else:
                for leaf in subnode:
                    issued_before = leaf.get('issued_before')
                    if issued_before is not None:
                        if issued_before > token_data['issued_at']:
                            return True
