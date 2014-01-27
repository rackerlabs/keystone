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

#TODO(ayoung) turn these two lists into the prameter names for the constructor
#for RevokeEvent
_names = ['user_id',
          'domain_id',
          'project_id',
          'trust_id',
          'consumer_id',
          'access_token_id',
          'expires_at',
          'role_id']


class RevokeEvent(object):
    def __init__(self, id,
                 user_id=None,
                 role_id=None,
                 issued_before=None,
                 expires_at=None,
                 domain_id=None,
                 project_id=None,
                 trust_id=None,
                 consumer_id=None,
                 access_token_id=None):
        for k, v in locals().copy().iteritems():
            setattr(self, k, v)
        self.revoked_at = timeutils.utcnow()
        if issued_before is None:
            self.issued_before = self.revoked_at

    def to_dict(self):
        keys = ['user_id',
                'role_id',
                'domain_id',
                'project_id']
        event = dict((key, self.__dict__[key]) for key in keys)
        event['id'] = self.id.__str__()
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

    def attr_keys(self):
        attr_keys = []
        for name in _names:
            key = "%s=%s" % (name, getattr(self, name) or 'None')
            attr_keys.append(key)
        return attr_keys


class EventIdentifier(object):
    def __init__(self, value=None):
        self._value = value or uuid.uuid4()

    def __str__(self):
        return str(self._value)


class RevokeMap(object):
    def add_event(self, event):
        revoke_map = self.revoke_map
        for key in event.attr_keys():
            sub = revoke_map.get(key)
            if sub is None:
                sub = dict()
                revoke_map[key] = sub
                revoke_map = sub
        revoke_map['issued_before'] = event.issued_before

    def __init__(self, revoke_events):
        revoke_map = dict()
        self.revoke_map = revoke_map
        for event in revoke_events:
            self.add_event(event)

    def is_revoked(self, token_data):

        def _check_revoked(revoke_map, names, token_data):
            name = names[0]
            names = names[1:]
            #iterate through the roles of the token.
            #First match is sufficient since role is at the
            #end of the name list
            if name == 'role_id':
                sub = None
                for role_id in token_data['roles']:
                    key = "%s=%s" % (name, role_id)
                    sub = revoke_map.get(key)
                    if sub is not None:
                        break
                if sub is None:
                    key = "%s=%s" % (name, 'None')
                    sub = revoke_map.get(key)
            else:
                key = "%s=%s" % (name, token_data.get(name) or 'None')
                sub = revoke_map.get(key)
                if sub is None:
                    #yes, this is redundant if it was None above
                    #but it is cheap
                    key = "%s=%s" % (name, 'None')
                    sub = revoke_map.get(key)
            if sub is None:
                return False
            if len(names) == 0:
                issued_before = sub.get('issued_before')
                if issued_before is None:
                    return False
                else:
                    #this is the leaf node
                    return issued_before > token_data['issued_at']
            else:
                return _check_revoked(sub, names, token_data)

        def _check_domain_ids(revoke_map, token_data):
            token_data['domain_id'] = token_data['user_domain_id']
            revoked = _check_revoked(revoke_map, _names, token_data)
            if not revoked:
                token_data['domain_id'] = token_data['project_domain_id']
                revoked = _check_revoked(revoke_map, _names, token_data)
            return revoked

        def _check_user_ids(revoke_map, token_data):
            revoked = _check_domain_ids(revoke_map, token_data)
        #check trust values against user_id based revocations
            if not revoked and token_data['trustor_id'] is not None:
                token_data['user_id'] = token_data['trustee_id']
                revoked = _check_domain_ids(revoke_map, token_data)
            if not revoked and token_data['trustee_id'] is not None:
                token_data['user_id'] = token_data['trustor_id']
                revoked = _check_domain_ids(revoke_map, token_data)
            return revoked

        revoke_map = self.revoke_map
        revoked = _check_user_ids(revoke_map, token_data)
        return revoked
