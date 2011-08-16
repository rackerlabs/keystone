#!/usr/bin/env python

"""Manages execution of keystone test suites"""
from keystone.test import KeystoneTest


class SQLTest(KeystoneTest):
    CONFIG_NAME = 'sql.conf.template'
    TEST_FILES = ('keystone.db',)


class MemcacheTest(KeystoneTest):
    CONFIG_NAME = 'memcache.conf.template'
    TEST_FILES = ('keystone.db',)


class LDAPTest(KeystoneTest):
    CONFIG_NAME = 'ldap.conf.template'
    TEST_FILES = ('keystone.db', 'ldap.db', 'ldap.db.db',)

TESTS = [
    SQLTest,
    #not running MemcacheTest,
    LDAPTest,
]

if __name__ == '__main__':
    for test_num, test_cls in enumerate(TESTS):
        print 'Starting test %d of %d with config: %s' % \
            (test_num + 1, len(TESTS), test_cls.CONFIG_NAME)
        test_cls().run()
