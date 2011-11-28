#!/usr/bin/env python

"""
To run all tests
    python run_tests.py

To run a single test:
    python run_tests.py
        functional.test_extensions:TestExtensions.test_extensions_json

To run a single test module:
    python run_tests.py functional.test_extensions

"""
import sys

from keystone.test import KeystoneTest, SQLTest, MemcacheTest, LDAPTest, \
                        SSLTest


TESTS = [
    SQLTest,
    # Waiting on instructions on how to start memcached in jenkins:
    # But tests pass
    # MemcacheTest,
    LDAPTest,
    SSLTest,
]


if __name__ == '__main__':
    if '-O' in sys.argv:
        filter = None
        for i in range(len(sys.argv)):
            if sys.argv[i] == '-O':
                if len(sys.argv) > i + 1:
                    filter = sys.argv[i + 1]
                    break
        if filter:
            TESTS = [t for t in TESTS if filter in str(t)]
            if not TESTS:
                print 'No tests by the name %s found' % filter
                exit()

    for test_num, test_cls in enumerate(TESTS):
        print 'Starting test %d of %d with config: %s' % \
            (test_num + 1, len(TESTS), test_cls.config_name)
        test_cls().run()
