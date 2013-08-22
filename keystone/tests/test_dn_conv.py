# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 Red Hat, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import unittest

from keystone.common import dn_conv

# OID's
#
# OID      Short Name Long Name
# -------- ---------- ----------------------
# 2.5.4.3  CN         commonName
# 2.5.4.6  C          countryName
# 2.5.4.7  L          localityName
# 2.5.4.8  ST         stateOrProvinceName
# 2.5.4.10 O          organizationName
# 2.5.4.11 OU         organizationalUnitName


class TestDNConversion(unittest.TestCase):
    def test_openssl_dn_check(self):
        rfc_dn = r'CN=user@example.com,L=Nashua,ST=New Hampshire,C=US'
        openssl_dn = r'/C=US/ST=New Hampshire/L=Nashua/CN=user@example.com'

        self.assertFalse(dn_conv.is_openssl_dn(rfc_dn))
        self.assertTrue(dn_conv.is_rfc_dn(rfc_dn))

        self.assertTrue(dn_conv.is_openssl_dn(openssl_dn))
        self.assertFalse(dn_conv.is_rfc_dn(openssl_dn))

        self.assertFalse(dn_conv.is_rfc_dn(''))
        self.assertFalse(dn_conv.is_rfc_dn('foo'))
        self.assertFalse(dn_conv.is_rfc_dn('=foo'))
        self.assertFalse(dn_conv.is_rfc_dn('foo="'))
        self.assertTrue(dn_conv.is_rfc_dn('foo='))

    def test_openssl_dn_check_numeric_oid(self):
        rfc_dn = (r'2.5.4.3=user@example.com,2.5.4.7=Nashua,'
                  r'2.5.4.8=New Hampshire,2.5.4.6=US')
        openssl_dn = (r'/2.5.4.6=US/2.5.4.8=New Hampshire/2.5.4.7=Nashua'
                      r'/2.5.4.3=user@example.com')

        self.assertFalse(dn_conv.is_openssl_dn(rfc_dn))
        self.assertTrue(dn_conv.is_openssl_dn(openssl_dn))

    def test_bad_input(self):
        rfc_dn = r'CN=user@example.com,L=Nashua,ST=New Hampshire,C=US'
        openssl_dn = r'/C=US/ST=New Hampshire/L=Nashua/CN=user@example.com'

        self.assertRaises(ValueError,
                          dn_conv.rfc_dn_to_openssl_dn,
                          openssl_dn)

        self.assertRaises(ValueError,
                          dn_conv.openssl_dn_to_rfc_dn,
                          rfc_dn)

    def test_conversion(self):
        rfc_dn = r'CN=user@example.com,L=Nashua,ST=New Hampshire,C=US'
        openssl_dn = r'/C=US/ST=New Hampshire/L=Nashua/CN=user@example.com'

        result = dn_conv.rfc_dn_to_openssl_dn(rfc_dn)
        self.assertEqual(result, openssl_dn)

        result = dn_conv.openssl_dn_to_rfc_dn(openssl_dn)
        self.assertEqual(result, rfc_dn)

    def test_conversion_no_reverse(self):
        rfc_dn = r'CN=user@example.com,L=Nashua,ST=New Hampshire,C=US'
        openssl_dn = r'/CN=user@example.com/L=Nashua/ST=New Hampshire/C=US'

        result = dn_conv.rfc_dn_to_openssl_dn(rfc_dn, reverse=False)
        self.assertEqual(result, openssl_dn)

    def test_conversion_numeric_oid(self):
        rfc_dn = (r'2.5.4.3=user@example.com,2.5.4.7=Nashua,'
                  r'2.5.4.8=New Hampshire,2.5.4.6=US')
        openssl_dn = (r'/2.5.4.6=US/2.5.4.8=New Hampshire/2.5.4.7=Nashua'
                      r'/2.5.4.3=user@example.com')

        result = dn_conv.rfc_dn_to_openssl_dn(rfc_dn)
        self.assertEqual(result, openssl_dn)

        result = dn_conv.openssl_dn_to_rfc_dn(openssl_dn)
        self.assertEqual(result, rfc_dn)

    def test_conversion_numeric_oid_no_reverse(self):
        rfc_dn = (r'2.5.4.3=user@example.com,2.5.4.7=Nashua,'
                  r'2.5.4.8=New Hampshire,2.5.4.6=US')
        openssl_dn = (r'/2.5.4.3=user@example.com/2.5.4.7=Nashua'
                      r'/2.5.4.8=New Hampshire/2.5.4.6=US')

        result = dn_conv.rfc_dn_to_openssl_dn(rfc_dn, reverse=False)
        self.assertEqual(result, openssl_dn)

    def test_no_multi_rdn(self):
        rfc_dn = r'CN=John Doe+UID=123456,DC=users,DC=OpenSSL,DC=org'
        openssl_dn = r'/DC=org/DC=OpenSSL/DC=users/UID=123456+CN=John Doe'

        result = dn_conv.rfc_dn_to_openssl_dn(rfc_dn)
        self.assertEqual(result, openssl_dn)

        # Note the escaped plus and equal signs in the multivalued RDN
        rfc_dn = r'UID=123456\+CN\=John Doe,DC=users,DC=OpenSSL,DC=org'
        result = dn_conv.openssl_dn_to_rfc_dn(openssl_dn)
        self.assertEqual(result, rfc_dn)

    def test_multi_rdn(self):
        rfc_dn = r'CN=John Doe+UID=123456,DC=users,DC=OpenSSL,DC=org'
        openssl_dn = r'/DC=org/DC=OpenSSL/DC=users/UID=123456+CN=John Doe'

        result = dn_conv.rfc_dn_to_openssl_dn(rfc_dn)
        self.assertEqual(result, openssl_dn)

        result = dn_conv.openssl_dn_to_rfc_dn(openssl_dn, multivalue_rdn=True)
        self.assertEqual(result, rfc_dn)

    def test_serial(self):
        rfc_dn = r'serialNumber=5+CN=SIDR test'
        openssl_dn = r'/CN=SIDR test+serialNumber=5'

        result = dn_conv.rfc_dn_to_openssl_dn(rfc_dn)
        self.assertEqual(result, openssl_dn)

        result = dn_conv.openssl_dn_to_rfc_dn(openssl_dn, multivalue_rdn=True)
        self.assertEqual(result, rfc_dn)
