# vim: tabstop=4 shiftwidth=4 softtabstop=4

from __future__ import absolute_import

#NOTE(bcwaldon): this could possible be moved inside the class so we
# don't have to install memcache to run the tests
import memcache

from keystone import config
from keystone import token


CONF = config.CONF.memcache


class Token(token.Driver):

    def __init__(self, client=None):
        self._memcache_client = client

    @property
    def client(self):
        return self._memcache_client or self._get_memcache_client()

    def _get_memcache_client(self):
        memcache_servers = CONF.servers.split(',')
        self._memcache_client = memcache.Client(memcache_servers, debug=0)
        return self._memcache_client

    @staticmethod
    def _prefix_token_id(token_id):
        return 'token-%s' % token_id

    def get_token(self, token_id):
        ptk = self._prefix_token_id(token_id)
        return self.client.get(ptk)

    def create_token(self, token_id, data):
        ptk = self._prefix_token_id(token_id)
        self.client.set(ptk, data)
        return data

    def delete_token(self, token_id):
        ptk = self._prefix_token_id(token_id)
        return self.client.delete(ptk)
