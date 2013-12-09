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


import enum
import six
import uuid


from keystone import exception
from keystone.openstack.common import timeutils
from oslo.config import cfg


class IdentityType(enum.IntEnum):
    none = 0
    domain = 1
    user = 2


class AssignmentType(enum.IntEnum):
    none = 0
    domain = 1
    project = 2
    trust = 5
    consumer = 6


class RevokeEvent(object):
    def __init__(self, id, 
                 identity_id=None,
                 identity_type=IdentityType.none,
                 assignment_id=None,
                 assignment_type=AssignmentType.none,
                 role_id=None,
                 issued_before=None,
                 expires_at=None):
        for k, v in locals().copy().iteritems():
            if v is not None:
                setattr(self, k, v)
        self.revoked_at = timeutils.isotime()

    @property
    def identity_type(self):
        return self._identity_type

    @identity_type.setter
    def identity_type(self, value):
        self._identity_type = IdentityType(value)

    @property
    def assignment_type(self):
        return self._assignment_type

    @assignment_type.setter
    def assignment_type(self, value):
        self._assignment_type = IdentityType(value)



class EventIdentifier():
    def __init__(self, value=None):
        if value is None:
            self.value = uuid.uuid4()
        else:
            self.value = value


