# -*- coding: utf-8 -*-
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

import os
import tempfile
import uuid

import fixtures
import ldap.dn
import mock
from testtools import matchers

from keystone.common import driver_hints
import keystone.conf
from keystone.identity.backends.ldap import common as common_ldap
from keystone.tests import unit
from keystone.tests.unit import default_fixtures
from keystone.tests.unit import fakeldap
from keystone.tests.unit.ksfixtures import database
from keystone.tests.unit.ksfixtures import ldapdb


CONF = keystone.conf.CONF


class MultiURLTests(unit.TestCase):
    """Test for setting multiple LDAP URLs."""

    def test_multiple_urls_with_comma_no_conn_pool(self):
        urls = 'ldap://localhost,ldap://backup.localhost'
        self.config_fixture.config(group='ldap', url=urls, use_pool=False)
        base_ldap = common_ldap.BaseLdap(CONF)
        ldap_connection = base_ldap.get_connection()
        self.assertEqual(urls, ldap_connection.conn.conn._uri)

    def test_multiple_urls_with_comma_with_conn_pool(self):
        urls = 'ldap://localhost,ldap://backup.localhost'
        self.config_fixture.config(group='ldap', url=urls, use_pool=True)
        base_ldap = common_ldap.BaseLdap(CONF)
        ldap_connection = base_ldap.get_connection()
        self.assertEqual(urls, ldap_connection.conn.conn_pool.uri)


class SslTlsTest(unit.TestCase):
    """Test for the SSL/TLS functionality in keystone.common.ldap.core."""

    @mock.patch.object(common_ldap.KeystoneLDAPHandler, 'simple_bind_s')
    @mock.patch.object(ldap.ldapobject.LDAPObject, 'start_tls_s')
    def _init_ldap_connection(self, config, mock_ldap_one, mock_ldap_two):
        # Attempt to connect to initialize python-ldap.
        base_ldap = common_ldap.BaseLdap(config)
        base_ldap.get_connection()

    def test_certfile_trust_tls(self):
        # We need this to actually exist, so we create a tempfile.
        (handle, certfile) = tempfile.mkstemp()
        self.addCleanup(os.unlink, certfile)
        self.addCleanup(os.close, handle)
        self.config_fixture.config(group='ldap',
                                   url='ldap://localhost',
                                   use_tls=True,
                                   tls_cacertfile=certfile)

        self._init_ldap_connection(CONF)

        # Ensure the cert trust option is set.
        self.assertEqual(certfile, ldap.get_option(ldap.OPT_X_TLS_CACERTFILE))

    def test_certdir_trust_tls(self):
        # We need this to actually exist, so we create a tempdir.
        certdir = self.useFixture(fixtures.TempDir()).path
        self.config_fixture.config(group='ldap',
                                   url='ldap://localhost',
                                   use_tls=True,
                                   tls_cacertdir=certdir)

        self._init_ldap_connection(CONF)

        # Ensure the cert trust option is set.
        self.assertEqual(certdir, ldap.get_option(ldap.OPT_X_TLS_CACERTDIR))

    def test_certfile_trust_ldaps(self):
        # We need this to actually exist, so we create a tempfile.
        (handle, certfile) = tempfile.mkstemp()
        self.addCleanup(os.unlink, certfile)
        self.addCleanup(os.close, handle)
        self.config_fixture.config(group='ldap',
                                   url='ldaps://localhost',
                                   use_tls=False,
                                   tls_cacertfile=certfile)

        self._init_ldap_connection(CONF)

        # Ensure the cert trust option is set.
        self.assertEqual(certfile, ldap.get_option(ldap.OPT_X_TLS_CACERTFILE))

    def test_certdir_trust_ldaps(self):
        # We need this to actually exist, so we create a tempdir.
        certdir = self.useFixture(fixtures.TempDir()).path
        self.config_fixture.config(group='ldap',
                                   url='ldaps://localhost',
                                   use_tls=False,
                                   tls_cacertdir=certdir)

        self._init_ldap_connection(CONF)

        # Ensure the cert trust option is set.
        self.assertEqual(certdir, ldap.get_option(ldap.OPT_X_TLS_CACERTDIR))


class LDAPPagedResultsTest(unit.TestCase):
    """Test the paged results functionality in keystone.common.ldap.core."""

    def setUp(self):
        super(LDAPPagedResultsTest, self).setUp()

        self.useFixture(ldapdb.LDAPDatabase())
        self.useFixture(database.Database(self.sql_driver_version_overrides))

        self.load_backends()
        self.load_fixtures(default_fixtures)

    def config_overrides(self):
        super(LDAPPagedResultsTest, self).config_overrides()
        self.config_fixture.config(group='identity', driver='ldap')

    def config_files(self):
        config_files = super(LDAPPagedResultsTest, self).config_files()
        config_files.append(unit.dirs.tests_conf('backend_ldap.conf'))
        return config_files

    @mock.patch.object(fakeldap.FakeLdap, 'search_ext')
    @mock.patch.object(fakeldap.FakeLdap, 'result3')
    def test_paged_results_control_api(self, mock_result3, mock_search_ext):
        mock_result3.return_value = ('', [], 1, [])

        self.config_fixture.config(group='ldap',
                                   page_size=1)

        conn = self.identity_api.user.get_connection()
        conn._paged_search_s('dc=example,dc=test',
                             ldap.SCOPE_SUBTREE,
                             'objectclass=*')


class CommonLdapTestCase(unit.BaseTestCase):
    """These test cases call functions in keystone.common.ldap."""

    def test_binary_attribute_values(self):
        result = [(
            'cn=junk,dc=example,dc=com',
            {
                'cn': ['junk'],
                'sn': [uuid.uuid4().hex],
                'mail': [uuid.uuid4().hex],
                'binary_attr': [b'\x00\xFF\x00\xFF']
            }
        ), ]
        py_result = common_ldap.convert_ldap_result(result)
        # The attribute containing the binary value should
        # not be present in the converted result.
        self.assertNotIn('binary_attr', py_result[0][1])

    def test_utf8_conversion(self):
        value_unicode = u'fäké1'
        value_utf8 = value_unicode.encode('utf-8')

        result_utf8 = common_ldap.utf8_encode(value_unicode)
        self.assertEqual(value_utf8, result_utf8)

        result_utf8 = common_ldap.utf8_encode(value_utf8)
        self.assertEqual(value_utf8, result_utf8)

        result_unicode = common_ldap.utf8_decode(value_utf8)
        self.assertEqual(value_unicode, result_unicode)

        result_unicode = common_ldap.utf8_decode(value_unicode)
        self.assertEqual(value_unicode, result_unicode)

        self.assertRaises(TypeError,
                          common_ldap.utf8_encode,
                          100)

        result_unicode = common_ldap.utf8_decode(100)
        self.assertEqual(u'100', result_unicode)

    def test_user_id_begins_with_0(self):
        user_id = '0123456'
        result = [(
            'cn=dummy,dc=example,dc=com',
            {
                'user_id': [user_id],
                'enabled': ['TRUE']
            }
        ), ]
        py_result = common_ldap.convert_ldap_result(result)
        # The user id should be 0123456, and the enabled
        # flag should be True
        self.assertIs(True, py_result[0][1]['enabled'][0])
        self.assertEqual(user_id, py_result[0][1]['user_id'][0])

    def test_user_id_begins_with_0_and_enabled_bit_mask(self):
        user_id = '0123456'
        bitmask = '225'
        expected_bitmask = 225
        result = [(
            'cn=dummy,dc=example,dc=com',
            {
                'user_id': [user_id],
                'enabled': [bitmask]
            }
        ), ]
        py_result = common_ldap.convert_ldap_result(result)
        # The user id should be 0123456, and the enabled
        # flag should be 225
        self.assertEqual(expected_bitmask, py_result[0][1]['enabled'][0])
        self.assertEqual(user_id, py_result[0][1]['user_id'][0])

    def test_user_id_and_bitmask_begins_with_0(self):
        user_id = '0123456'
        bitmask = '0225'
        expected_bitmask = 225
        result = [(
            'cn=dummy,dc=example,dc=com',
            {
                'user_id': [user_id],
                'enabled': [bitmask]
            }
        ), ]
        py_result = common_ldap.convert_ldap_result(result)
        # The user id should be 0123456, and the enabled
        # flag should be 225, the 0 is dropped.
        self.assertEqual(expected_bitmask, py_result[0][1]['enabled'][0])
        self.assertEqual(user_id, py_result[0][1]['user_id'][0])

    def test_user_id_and_user_name_with_boolean_string(self):
        boolean_strings = ['TRUE', 'FALSE', 'true', 'false', 'True', 'False',
                           'TrUe' 'FaLse']
        for user_name in boolean_strings:
            user_id = uuid.uuid4().hex
            result = [(
                'cn=dummy,dc=example,dc=com',
                {
                    'user_id': [user_id],
                    'user_name': [user_name]
                }
            ), ]
            py_result = common_ldap.convert_ldap_result(result)
            # The user name should still be a string value.
            self.assertEqual(user_name, py_result[0][1]['user_name'][0])


class LDAPFilterQueryCompositionTest(unit.TestCase):
    """These test cases test LDAP filter generation."""

    def setUp(self):
        super(LDAPFilterQueryCompositionTest, self).setUp()

        self.base_ldap = common_ldap.BaseLdap(self.config_fixture.conf)

        # The tests need an attribute mapping to use.
        self.attribute_name = uuid.uuid4().hex
        self.filter_attribute_name = uuid.uuid4().hex
        self.base_ldap.attribute_mapping = {
            self.attribute_name: self.filter_attribute_name
        }

    def test_return_query_with_no_hints(self):
        hints = driver_hints.Hints()
        # NOTE: doesn't have to be a real query, we just need to make sure the
        # same string is returned if there are no hints.
        query = uuid.uuid4().hex
        self.assertEqual(query,
                         self.base_ldap.filter_query(hints=hints, query=query))

        # make sure the default query is an empty string
        self.assertEqual('', self.base_ldap.filter_query(hints=hints))

    def test_filter_with_empty_query_and_hints_set(self):
        hints = driver_hints.Hints()
        username = uuid.uuid4().hex
        hints.add_filter(name=self.attribute_name,
                         value=username,
                         comparator='equals',
                         case_sensitive=False)
        expected_ldap_filter = '(&(%s=%s))' % (
            self.filter_attribute_name, username)
        self.assertEqual(expected_ldap_filter,
                         self.base_ldap.filter_query(hints=hints))

    def test_filter_with_both_query_and_hints_set(self):
        hints = driver_hints.Hints()
        # NOTE: doesn't have to be a real query, we just need to make sure the
        # filter string is concatenated correctly
        query = uuid.uuid4().hex
        username = uuid.uuid4().hex
        expected_result = '(&%(query)s(%(user_name_attr)s=%(username)s))' % (
            {'query': query,
             'user_name_attr': self.filter_attribute_name,
             'username': username})
        hints.add_filter(self.attribute_name, username)
        self.assertEqual(expected_result,
                         self.base_ldap.filter_query(hints=hints, query=query))

    def test_filter_with_hints_and_query_is_none(self):
        hints = driver_hints.Hints()
        username = uuid.uuid4().hex
        hints.add_filter(name=self.attribute_name,
                         value=username,
                         comparator='equals',
                         case_sensitive=False)
        expected_ldap_filter = '(&(%s=%s))' % (
            self.filter_attribute_name, username)
        self.assertEqual(expected_ldap_filter,
                         self.base_ldap.filter_query(hints=hints, query=None))
