# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
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

import ldap
import ldap.modlist
import nose.exc
import subprocess

from keystone import config
from keystone.identity.backends import ldap as identity_ldap
from keystone import test
from keystone import exception

import default_fixtures
import test_backend_ldap


CONF = config.CONF


def create_object(dn, attrs):
    conn = ldap.initialize(CONF.ldap.url)
    conn.simple_bind_s(CONF.ldap.user, CONF.ldap.password)
    ldif = ldap.modlist.addModlist(attrs)
    conn.add_s(dn, ldif)
    conn.unbind_s()


class LiveLDAPIdentity(test_backend_ldap.LDAPIdentity):

    def clear_database(self):
        devnull = open('/dev/null', 'w')
        subprocess.call(['ldapdelete',
                         '-x',
                         '-D', CONF.ldap.user,
                         '-H', CONF.ldap.url,
                         '-w', CONF.ldap.password,
                         '-r', CONF.ldap.suffix],
                        stderr=devnull)

        if CONF.ldap.suffix.startswith('ou='):
            tree_dn_attrs = {'objectclass': 'organizationalUnit',
                             'ou': 'openstack'}
        else:
            tree_dn_attrs = {'objectclass': ['dcObject', 'organizationalUnit'],
                             'dc': 'openstack',
                             'ou': 'openstack'}
        create_object(CONF.ldap.suffix, tree_dn_attrs)
        create_object(CONF.ldap.user_tree_dn,
                      {'objectclass': 'organizationalUnit',
                      'ou': 'Users'})
        create_object(CONF.ldap.role_tree_dn,
                      {'objectclass': 'organizationalUnit',
                      'ou': 'Roles'})
        create_object(CONF.ldap.tenant_tree_dn,
                      {'objectclass': 'organizationalUnit',
                      'ou': 'Projects'})

        # NOTE(crazed): This feature is currently being added
        create_object("ou=Groups,%s" % CONF.ldap.suffix,
                      {'objectclass': 'organizationalUnit',
                      'ou': 'Groups'})

    def _set_config(self):
        self.config([test.etcdir('keystone.conf.sample'),
                     test.testsdir('test_overrides.conf'),
                     test.testsdir('backend_liveldap.conf')])

    def test_build_tree(self):
        """Regression test for building the tree names
        """
        #logic is different from the fake backend.
        user_api = identity_ldap.UserApi(CONF)
        self.assertTrue(user_api)
        self.assertEquals(user_api.tree_dn, CONF.ldap.user_tree_dn)

    def tearDown(self):
        test.TestCase.tearDown(self)

    def test_user_enable_attribute_mask(self):
        raise nose.exc.SkipTest('Test is for Active Directory Only')

    def test_configurable_allowed_project_actions(self):
        raise nose.exc.SkipTest('Blocked by bug 1155234')

    def test_project_crud(self):
        raise nose.exc.SkipTest('Blocked by bug 1155234')

    def test_ldap_dereferencing(self):
        alt_users_ldif = {'objectclass': ['top', 'organizationalUnit'],
                          'ou': 'alt_users'}
        alt_fake_user_ldif = {'objectclass': ['person', 'inetOrgPerson'],
                              'cn': 'alt_fake1',
                              'sn': 'alt_fake1'}
        aliased_users_ldif = {'objectclass': ['alias', 'extensibleObject'],
                              'aliasedobjectname': "ou=alt_users,%s" %
                              CONF.ldap.suffix}
        create_object("ou=alt_users,%s" % CONF.ldap.suffix, alt_users_ldif)
        create_object("%s=alt_fake1,ou=alt_users,%s" %
                      (CONF.ldap.user_id_attribute, CONF.ldap.suffix),
                      alt_fake_user_ldif)
        create_object("ou=alt_users,%s" % CONF.ldap.user_tree_dn,
                      aliased_users_ldif)

        CONF.ldap.query_scope = 'sub'
        CONF.ldap.deref_opt = 'never'
        self.identity_api = identity_ldap.Identity()
        self.assertRaises(exception.UserNotFound,
                          self.identity_api.get_user,
                          'alt_fake1')

        CONF.ldap.deref_opt = 'searching'
        self.identity_api = identity_ldap.Identity()
        user_ref = self.identity_api.get_user('alt_fake1')
        self.assertEqual(user_ref['id'], 'alt_fake1')

        CONF.ldap.deref_opt = 'always'
        self.identity_api = identity_ldap.Identity()
        user_ref = self.identity_api.get_user('alt_fake1')
        self.assertEqual(user_ref['id'], 'alt_fake1')

