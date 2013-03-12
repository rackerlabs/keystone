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

import default_fixtures
import test_backend_ldap


CONF = config.CONF

def delete_object(dn):
    devnull = open('/dev/null', 'w')
    subprocess.call(['ldapdelete',
                     '-x',
                     '-D', CONF.ldap.user,
                     '-H', CONF.ldap.url,
                     '-w', CONF.ldap.password,
                     dn],
                    stderr=devnull)


def clear_live_database():
    roles = ['keystone_admin', 'fake1', 'fake2', 'useless', 'admin', 'member',
             '9fe2ff9ee4384b1894a90878d3e92bab',
             '02def574ec544446bf6d7cb685ad8a70',
             'cdb7cbfb098644c4baf2100d94411b12',
             'c66397bbab37418da7eee1606b3f2adf']
    groups = ['baz', 'bar', 'tenent4add', 'fake1', 'fake2', 'mtu']
    users = ['foo', 'two', 'fake1', 'fake2', 'no_meta', 'badguy', 'sna']

    for group in groups:
        for role in roles:
            delete_object('cn=%s,cn=%s,%s' % (role, group,
                          CONF.ldap.tenant_tree_dn))
        delete_object('cn=%s,%s' % (group, CONF.ldap.tenant_tree_dn))

    for user in users:
        delete_object('cn=%s,%s' % (user, CONF.ldap.user_tree_dn))

    for role in roles:
        delete_object('cn=%s,%s' % (role, CONF.ldap.role_tree_dn))


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
