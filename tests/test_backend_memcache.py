import time
import datetime

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
        if obj is not None:
            now = time.mktime(datetime.datetime.now().timetuple())
            if obj[1] == 0 or obj[1] > now:
                return obj[0]


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
