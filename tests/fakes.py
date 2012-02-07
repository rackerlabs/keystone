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
        del self.cache[key]
