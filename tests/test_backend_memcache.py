import uuid

from keystone import test
from keystone.token.backends import memcache as token_memcache


class MemcacheClient(object):
    """Replicates a tiny subset of memcached client interface."""

    def __init__(self, *args, **kwargs):
        """Ignores the passed in args."""
        self.cache = {}

    def get(self, key):
        """Retrieves the value for a key or None."""
        return self.cache.get(key)

    def set(self, key, value):
        """Sets the value for a key."""
        self.cache[key] = value
        return True

    def delete(self, key):
        try:
            del self.cache[key]
        except KeyError:
            #NOTE(bcwaldon): python-memcached always returns the same value
            pass


class MemcacheToken(test.TestCase):
    def setUp(self):
        super(MemcacheToken, self).setUp()
        fake_client = MemcacheClient()
        self.token_api = token_memcache.Token(client=fake_client)

    def test_token_crud(self):
        token_id = uuid.uuid4().hex
        data = {'id': token_id, 'a': 'b'}
        data_ref = self.token_api.create_token(token_id, data)
        self.assertDictEquals(data_ref, data)

        new_data_ref = self.token_api.get_token(token_id)
        self.assertEquals(new_data_ref, data)

        self.token_api.delete_token(token_id)
        deleted_data_ref = self.token_api.get_token(token_id)
        self.assertTrue(deleted_data_ref is None)

    def test_token_delete_nonexistant(self):
        token_id = uuid.uuid4().hex
        self.token_api.delete_token(token_id)
