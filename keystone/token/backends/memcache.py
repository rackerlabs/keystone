# vim: tabstop=4 shiftwidth=4 softtabstop=4

from __future__ import absolute_import

import memcache
from keystone import config
from keystone import token


CONF = config.CONF.memcache


class Token(token.Driver):

    def __init__(self):
        memcache_servers = CONF.servers.split(',')
        self.mc = memcache.Client(memcache_servers, debug=0)

    # Public interface
    def get_token(self, token_id):
        return self.mc.get('token-%s' % token_id)

    def create_token(self, token_id, data):
        self.mc.set('token-%s' % token_id, data)
        return data

    def delete_token(self, token_id):
        return self.mc.delete('token-%s' % token_id)
