# vim: tabstop=4 shiftwidth=4 softtabstop=4

import subprocess

from keystone import test
from keystone.identity.backends import ldap as identity_ldap

import default_fixtures
import test_backend


def delete_object(conf, name):
    devnull = open('/dev/null', 'w')
    dn = '%s,%s' % (name, conf.ldap.suffix)
    subprocess.call(['ldapdelete',
                     '-x',
                     '-D', conf.ldap.user,
                     '-H', conf.ldap.url,
                     '-w', conf.ldap.password,
                     dn],
                    stderr=devnull)


def clear_live_database(conf):
    roles = ['keystone_admin']
    groups = ['baz', 'bar', 'tenent4add','fake1','fake2']
    users = ['foo', 'two','fake1','fake2']
    roles = ['keystone_admin', 'useless']

    for group in groups:
        for role in roles:
            delete_object(conf, 'cn=%s,cn=%s,ou=Groups' % (role, group))
        delete_object(conf, 'cn=%s,ou=Groups' % group)

    for user in users:
        delete_object(conf, 'cn=%s,ou=Users' % user)

    for role in roles:
        delete_object(conf, 'cn=%s,ou=Roles' % role)


class LDAPIdentity(test.TestCase, test_backend.IdentityTests):
    def setUp(self):
        super(LDAPIdentity, self).setUp([
                test.etcdir('keystone.conf'),
                test.testsdir('test_overrides.conf'),
                test.testsdir('backend_liveldap.conf')])
        clear_live_database(self.conf)
        self.identity_api = identity_ldap.Identity(self.conf)
        self.load_fixtures(default_fixtures)
        self.user_foo = {'id': 'foo',
                         'name': 'FOO',
                         'password': 'foo2',
                         'tenants': ['bar']}

    def tearDown(self):
        test.TestCase.tearDown(self)
