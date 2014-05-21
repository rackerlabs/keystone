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

import ldap.dn

from keystone import tests
from keystone.common import ldap as ks_ldap


class DnCompareTest(tests.BaseTestCase):
    """Tests for the DN comparison functions in keystone.common.ldap.core."""

    def test_prep(self):
        # prep_case_insensitive returns the string with spaces at the front and
        # end if it's already lowercase and no insignificant characters.
        value = 'lowercase value'
        exp_value = ' ' + value + ' '
        self.assertEqual(exp_value, ks_ldap.prep_case_insensitive(value))

    def test_prep_lowercase(self):
        # prep_case_insensitive returns the string with spaces at the front and
        # end and lowercases the value.
        value = 'UPPERCASE VALUE'
        exp_value = ' ' + value.lower() + ' '
        self.assertEqual(exp_value, ks_ldap.prep_case_insensitive(value))

    def test_prep_insignificant(self):
        # prep_case_insensitive remove insignificant spaces.
        value = 'before   after'
        exp_value = ' before after '
        self.assertEqual(exp_value, ks_ldap.prep_case_insensitive(value))

    def test_prep_insignificant_pre_post(self):
        # prep_case_insensitive remove insignificant spaces.
        value = '   value   '
        exp_value = ' value '
        self.assertEqual(exp_value, ks_ldap.prep_case_insensitive(value))

    def test_ava_equal_same(self):
        # is_ava_equal returns True if the two values are the same.
        value = 'val1'
        self.assertTrue(ks_ldap.is_ava_equal('cn', value, value))

    def test_ava_equal_complex(self):
        # is_ava_equal returns True if the two values are the same using a
        # value that's got different capitalization and insignificant chars.
        val1 = 'before   after'
        val2 = '  BEFORE  afTer '
        self.assertTrue(ks_ldap.is_ava_equal('cn', val1, val2))

    def test_ava_different(self):
        # is_ava_equal returns False if the values aren't the same.
        self.assertFalse(ks_ldap.is_ava_equal('cn', 'val1', 'val2'))

    def test_rdn_same(self):
        # is_rdn_equal returns True if the two values are the same.
        rdn = ldap.dn.str2dn('cn=val1')[0]
        self.assertTrue(ks_ldap.is_rdn_equal(rdn, rdn))

    def test_rdn_diff_length(self):
        # is_rdn_equal returns False if the RDNs have a different number of
        # AVAs.
        rdn1 = ldap.dn.str2dn('cn=cn1')[0]
        rdn2 = ldap.dn.str2dn('cn=cn1+ou=ou1')[0]
        self.assertFalse(ks_ldap.is_rdn_equal(rdn1, rdn2))

    def test_rdn_multi_ava_same_order(self):
        # is_rdn_equal returns True if the RDNs have the same number of AVAs
        # and the values are the same.
        rdn1 = ldap.dn.str2dn('cn=cn1+ou=ou1')[0]
        rdn2 = ldap.dn.str2dn('cn=CN1+ou=OU1')[0]
        self.assertTrue(ks_ldap.is_rdn_equal(rdn1, rdn2))

    def test_rdn_multi_ava_diff_order(self):
        # is_rdn_equal returns True if the RDNs have the same number of AVAs
        # and the values are the same, even if in a different order
        rdn1 = ldap.dn.str2dn('cn=cn1+ou=ou1')[0]
        rdn2 = ldap.dn.str2dn('ou=OU1+cn=CN1')[0]
        self.assertTrue(ks_ldap.is_rdn_equal(rdn1, rdn2))

    def test_rdn_multi_ava_diff_type(self):
        # is_rdn_equal returns False if the RDNs have the same number of AVAs
        # and the attribute types are different.
        rdn1 = ldap.dn.str2dn('cn=cn1+ou=ou1')[0]
        rdn2 = ldap.dn.str2dn('cn=cn1+sn=sn1')[0]
        self.assertFalse(ks_ldap.is_rdn_equal(rdn1, rdn2))

    def test_rdn_attr_type_case_diff(self):
        # is_rdn_equal returns True for same RDNs even when attr type case is
        # different.
        rdn1 = ldap.dn.str2dn('cn=cn1')[0]
        rdn2 = ldap.dn.str2dn('CN=cn1')[0]
        self.assertTrue(ks_ldap.is_rdn_equal(rdn1, rdn2))

    def test_rdn_attr_type_alias(self):
        # is_rdn_equal returns False for same RDNs even when attr type alias is
        # used. Note that this is a limitation since an LDAP server should
        # consider them equal.
        rdn1 = ldap.dn.str2dn('cn=cn1')[0]
        rdn2 = ldap.dn.str2dn('2.5.4.3=cn1')[0]
        self.assertFalse(ks_ldap.is_rdn_equal(rdn1, rdn2))

    def test_dn_same(self):
        # is_dn_equal returns True if the DNs are the same.
        dn = ldap.dn.str2dn('cn=Babs Jansen,ou=OpenStack')
        self.assertTrue(ks_ldap.is_dn_equal(dn, dn))

    def test_dn_diff_length(self):
        # is_dn_equal returns False if the DNs don't have the same number of
        # RDNs
        dn1 = ldap.dn.str2dn('cn=Babs Jansen,ou=OpenStack')
        dn2 = ldap.dn.str2dn('cn=Babs Jansen,ou=OpenStack,dc=example.com')
        self.assertFalse(ks_ldap.is_dn_equal(dn1, dn2))

    def test_dn_equal_rdns(self):
        # is_dn_equal returns True if the DNs have the same number of RDNs
        # and each RDN is the same.
        dn1 = ldap.dn.str2dn('cn=Babs Jansen,ou=OpenStack+cn=OpenSource')
        dn2 = ldap.dn.str2dn('CN=Babs Jansen,cn=OpenSource+ou=OpenStack')
        self.assertTrue(ks_ldap.is_dn_equal(dn1, dn2))

    def test_dn_str_equal(self):
        # is_dn_str_equal uses DN strings rather than DNs.
        dn_str1 = 'cn=Babs Jansen,ou=OpenStack+cn=OpenSource'
        dn_str2 = 'CN=Babs Jansen,cn=OpenSource+ou=OpenStack'
        self.assertTrue(ks_ldap.is_dn_str_equal(dn_str1, dn_str2))

    def test_dn_under_child(self):
        # is_dn_under returns True if descendant_dn is a child of dn.
        child = ldap.dn.str2dn('cn=Babs Jansen,ou=OpenStack')
        parent = ldap.dn.str2dn('ou=OpenStack')
        self.assertTrue(ks_ldap.is_dn_under(child, parent))

    def test_dn_under_parent(self):
        # is_dn_under returns False if descendant_dn is a parent of dn.
        child = ldap.dn.str2dn('cn=Babs Jansen,ou=OpenStack')
        parent = ldap.dn.str2dn('ou=OpenStack')
        self.assertFalse(ks_ldap.is_dn_under(parent, child))

    def test_dn_under_same(self):
        # is_dn_under returns False if DNs are the same.
        dn = ldap.dn.str2dn('cn=Babs Jansen,ou=OpenStack')
        self.assertFalse(ks_ldap.is_dn_under(dn, dn))

    def test_dn_under_not_parent(self):
        # is_dn_under returns False if descendant_dn is not under the dn
        child = ldap.dn.str2dn('cn=Babs Jansen,ou=OpenStack')
        parent = ldap.dn.str2dn('dc=example.com')
        self.assertFalse(ks_ldap.is_dn_under(child, parent))

    def test_dn_under_descendant(self):
        # is_dn_under returns True if descendant_dn is a descendant of dn.
        dn_str = 'cn=Babs Jansen,ou=Keystone,ou=OpenStack,dc=example.com'
        descendant = ldap.dn.str2dn(dn_str)
        dn = ldap.dn.str2dn('ou=OpenStack,dc=example.com')
        self.assertTrue(ks_ldap.is_dn_under(descendant, dn))
