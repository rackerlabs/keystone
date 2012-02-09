# vim: tabstop=4 shiftwidth=4 softtabstop=4

import datetime

from keystone import token
from keystone.common import kvs


class Token(kvs.Base, token.Driver):
    # Public interface
    def get_token(self, token_id):
        token = self.db.get('token-%s' % token_id)
        if token is not None and token['expire_at'] > datetime.datetime.now():
            return token

    def create_token(self, token_id, data):
        if 'expire_at' not in data:
            data['expire_at'] = self.get_default_expire_time()
        self.db.set('token-%s' % token_id, data)
        return data

    def delete_token(self, token_id):
        return self.db.delete('token-%s' % token_id)
