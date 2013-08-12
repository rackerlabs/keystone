# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
# Copyright 2013 IBM Corp.
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

from keystone.common import ldap as common_ldap
from keystone.tests import core as test


class DnEqualsTest(test.TestCase):
    def test_equals(self):
        # Two DNs are equal even if the attributes are capitalized differently.
        id_ = uuid.uuid4().hex
        dn1 = 'CN=%s,OU=Groups,DC=sys1' % id_
        dn2 = 'cn=%s,ou=Groups,dc=sys1' % id_
        self.assertTrue(common_ldap.dn_equals(dn1, dn2))

    def test_not_equals(self):
        # Two DNs are not equal when the attribute value is different.
        dn1 = 'CN=%s,OU=Groups,DC=sys1' % uuid.uuid4().hex
        dn2 = 'CN=%s,OU=Groups,DC=sys1' % uuid.uuid4().hex
        self.assertFalse(common_ldap.dn_equals(dn1, dn2))
