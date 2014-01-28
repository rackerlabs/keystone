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
_names = ['trust_id',
          'consumer_id',
          'access_token_id',
          'expires_at',
          'domain_id',
          'project_id',
          'user_id',
          'role_id']


#additional arguments for creating a RevokeEvent
_event_args = ['id', 'issued_before', 'revoked_at']


_token_keys = ['user_domain_id',
               'project_domain_id',
               'issued_at',
               'trustor_id',
               'trustee_id']


revoke_keys = _names + _event_args


def blank_token_data(issued_at):
    token_data = dict()
    for name in _names:
        token_data[name] = None
    for name in _token_keys:
        token_data[name] = None
    #required field
    token_data['issued_at'] = issued_at
    return token_data


class RevokeEvent(object):
    def __init__(self, **kwargs):
        for k in revoke_keys:
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

    def key_for_name(self, name):
        return "%s=%s" % (name, getattr(self, name) or 'None')

    def attr_keys(self):
        attr_keys = []
        for name in _names:
            key = self.key_for_name(name)
            attr_keys.append(key)
        return attr_keys

    def matches(self, token_values):
        """See if the token matches the revocation self.

        Compare each attribute from the self with the corresponding
        value from the token.  If the self does not have a value for
        the attribute, a match is still possible.  If the self has a
        value for the attribute, and it does not match the token, no match
        is possible, so skip the remaining checks.

        :param self one revocation self to match
        :param token_values dictionary with set of values taken from the
        token
        :returns if the token matches the revocation self, indicating the
        token has been revoked
        """

        #something has to match in order to revoke the token
        matched = False

        #The token has three attributes that can match the user_id
        if self.user_id is not None:
            user_id_matched = False
            for attribute_name in ['user_id', 'trustor_id', 'trustee_id']:
                if self.user_id == token_values[attribute_name]:
                    user_id_matched = True
                    break
            if not user_id_matched:
                return False
            else:
                matched = True

        #The token has two attributes that can match the domain_id
        if self.domain_id is not None:
            dom_id_matched = False
            for attribute_name in ['user_domain_id', 'project_domain_id']:
                if self.domain_id == token_values[attribute_name]:
                    dom_id_matched = True
                    break
            if not dom_id_matched:
                return False
            else:
                matched = True

        #If any one check does not match, the while token does
        #not match the self. The numerous return False indicate
        # that the token is still valid and short-circuits the
        #rest of the logic.
        attribute_names = ['project_id',
                           'expires_at', 'trust_id', 'consumer_id',
                           'access_token_id']
        for attribute_name in attribute_names:
            if getattr(self, attribute_name) is not None:
                if (getattr(self, attribute_name) !=
                        token_values[attribute_name]):
                            return False
                else:
                    matched = True

        if self.role_id is not None:
            roles = token_values['roles']
            role_found = False
            for role in roles:
                if self.role_id == role:
                    role_found = True
                    break
            if role_found:
                matched = True
            else:
                return False
        matched = (matched and
                   self.issued_before > token_values['issued_at'])
        return matched


class EventIdentifier(object):
    def __init__(self, value=None):
        self._value = value or uuid.uuid4()

    def __str__(self):
        return str(self._value)


class RevokeTree(object):

    def __init__(self, revoke_events=[]):
        self.revoke_map = dict()
        self.add_events(revoke_events)

    def add_event(self, event):
        revoke_map = self.revoke_map
        for key in event.attr_keys():
            sub = revoke_map.get(key)
            if sub is None:
                sub = dict()
                revoke_map[key] = sub
            revoke_map = sub
        revoke_map['issued_before'] = event.issued_before
        return event

    def remove_event(self, event):
        def _remove_event(revoke_map, names, event):
            if len(names) == 0:
                    revoke_map.pop('issued_before')
            else:
                name = names[0]
                names = names[1:]
                key = event.key_for_name(name)
                sub = revoke_map.get(key)
                if sub is not None:
                    _remove_event(sub, names, event)
                    if(not any(sub)):
                        revoke_map.pop(key)

        _remove_event(self.revoke_map, _names, event, )

    def add_events(self, revoke_events):
        for event in revoke_events:
            self.add_event(event)

    def is_revoked(self, token_data):

            #iterate through the roles of the token.
            #First match is sufficient since role is at the
            #end of the name list
        def _check_roles(revoke_map, names, token_data):
            matched = False
            key = "%s=%s" % ('role_id', 'None')
            sub = revoke_map.get(key)
            matched = _check_revoked(sub, names, token_data)
            if matched:
                return True
            for role_id in token_data['roles']:
                key = "%s=%s" % ('role_id', role_id)
                sub = revoke_map.get(key)
                matched = matched or _check_revoked(sub, names, token_data)
                if matched:
                    return True

        def _check_issued_before(revoke_map, token_data):
            issued_before = revoke_map.get('issued_before')
            if issued_before is None:
                matched = False
            else:
                matched = issued_before > token_data['issued_at']
            return matched

        def _check_standard_attribute(revoke_map, names, token_data, name):
            key = "%s=%s" % (name, 'None')
            sub = revoke_map.get(key)
            matched = _check_revoked(sub, names, token_data)
            if not matched and token_data.get(name) is not None:
                key = "%s=%s" % (name, token_data[name])
                sub = revoke_map.get(key)
                matched = _check_revoked(sub, names, token_data)
            return matched

        def _check_domain_ids(revoke_map, names, token_data):
            token_data['domain_id'] = token_data['user_domain_id']
            matched = _check_standard_attribute(
                revoke_map, names, token_data, 'domain_id')
            if not matched:
                token_data['domain_id'] = token_data['project_domain_id']
                matched = _check_standard_attribute(
                    revoke_map, names, token_data, 'domain_id')
            return matched

        def _check_user_ids(revoke_map, names, token_data):
            matched = _check_standard_attribute(
                revoke_map, names, token_data, 'user_id')
        #check trust values against user_id based revocations
            if not matched and token_data['trustor_id'] is not None:
                token_data['user_id'] = token_data['trustor_id']
                matched = _check_standard_attribute(
                    revoke_map, names, token_data, 'user_id')
            if not matched and token_data['trustee_id'] is not None:
                token_data['user_id'] = token_data['trustee_id']
                matched = _check_standard_attribute(
                    revoke_map, names, token_data, 'user_id')
            return matched

        def _check_revoked(revoke_map, names, token_data):
            if revoke_map is None:
                return False
            if len(names) == 0:
                #leaf node
                return _check_issued_before(revoke_map, token_data)

            name = names[0]
            names = names[1:]
            matched = False

            if name == 'role_id':
                matched = _check_roles(revoke_map, names, token_data)
            elif name == 'user_id':
                matched = _check_user_ids(revoke_map, names, token_data)
            elif name == 'domain_id':
                matched = _check_domain_ids(revoke_map, names, token_data)
            else:
                matched = _check_standard_attribute(
                    revoke_map, names, token_data, name)
            return matched

        return _check_revoked(self.revoke_map, _names, token_data)
