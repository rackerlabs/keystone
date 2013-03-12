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

import subprocess

from keystone import config
from keystone.identity.backends import ldap as identity_ldap
from keystone import test
from keystone import exception

import default_fixtures
import test_backend_ldap


CONF = config.CONF


def delete_object(name):
    devnull = open('/dev/null', 'w')
    dn = '%s,%s' % (name, CONF.ldap.suffix)
    subprocess.call(['ldapdelete',
                     '-x',
                     '-D', CONF.ldap.user,
                     '-H', CONF.ldap.url,
                     '-w', CONF.ldap.password,
                     dn],
                    stderr=devnull)


def clear_live_database():
    roles = ['keystone_admin', 'fake1', 'fake2', 'useless']
    groups = ['baz', 'bar', 'tenent4add', 'fake1', 'fake2']
    users = ['foo', 'two', 'fake1', 'fake2', 'no_meta']

    for group in groups:
        for role in roles:
            delete_object('cn=%s,cn=%s,ou=Groups' % (role, group))
        delete_object('cn=%s,ou=Groups' % group)

    for user in users:
        delete_object('cn=%s,ou=Users' % user)

    for role in roles:
        delete_object('cn=%s,ou=Roles' % role)


class LiveLDAPIdentity(test_backend_ldap.LDAPIdentity):
    def setUp(self):
        super(LiveLDAPIdentity, self).setUp()
        self.config([test.etcdir('keystone.conf.sample'),
                     test.testsdir('test_overrides.conf'),
                     test.testsdir('backend_liveldap.conf')])
        clear_live_database()
        self.identity_api = identity_ldap.Identity()
        self.load_fixtures(default_fixtures)

    def tearDown(self):
        test.TestCase.tearDown(self)

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
