# vim: tabstop=4 shiftwidth=4 softtabstop=4

import time
import datetime

from keystone import exception
from keystone import test
from keystone.token.backends import memcache as token_memcache

import test_backend


class MemcacheClient(object):
    """Replicates a tiny subset of memcached client interface."""

    def __init__(self, *args, **kwargs):
        """Ignores the passed in args."""
        self.cache = {}

    def get(self, key):
        """Retrieves the value for a key or None."""
        obj = self.cache.get(key)
        now = time.mktime(datetime.datetime.now().timetuple())
        if obj and (obj[1] == 0 or obj[1] > now):
            return obj[0]
        else:
            raise exception.TokenNotFound(token_id=key)

    def set(self, key, value, time=0):
        """Sets the value for a key."""
        self.cache[key] = (value, time)
        return True

    def delete(self, key):
        try:
            del self.cache[key]
        except KeyError:
            #NOTE(bcwaldon): python-memcached always returns the same value
            pass


class MemcacheToken(test.TestCase, test_backend.TokenTests):
    def setUp(self):
        super(MemcacheToken, self).setUp()
        fake_client = MemcacheClient()
        self.token_api = token_memcache.Token(client=fake_client)
