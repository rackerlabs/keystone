# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import datetime
import uuid

import memcache

from keystone.common import utils
from keystone import exception
from keystone.openstack.common import timeutils
from keystone import test
from keystone import token
from keystone.token.backends import memcache as token_memcache

import test_backend
import test_utils


class MemcacheClient(object):
    """Replicates a tiny subset of memcached client interface."""

    def __init__(self, *args, **kwargs):
        """Ignores the passed in args."""
        self.cache = {}

    def add(self, key, value):
        if self.get(key):
            return False
        return self.set(key, value)

    def append(self, key, value):
        existing_value = self.get(key)
        if existing_value:
            self.set(key, existing_value + value)
            return True
        return False

    def check_key(self, key):
        if not isinstance(key, str):
            raise memcache.Client.MemcachedStringEncodingError()

    def get(self, key):
        """Retrieves the value for a key or None."""
        self.check_key(key)
        obj = self.cache.get(key)
        now = utils.unixtime(timeutils.utcnow())
        if obj and (obj[1] == 0 or obj[1] > now):
            return obj[0]

    def set(self, key, value, time=0):
        """Sets the value for a key."""
        self.check_key(key)
        self.cache[key] = (value, time)
        return True

    def delete(self, key):
        self.check_key(key)
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

    def test_create_unicode_token_id(self):
        token_id = unicode(self._create_token_id())
        data = {'id': token_id, 'a': 'b',
                'user': {'id': 'testuserid'}}
        self.token_api.create_token(token_id, data)
        self.token_api.get_token(token_id)

    def test_create_unicode_user_id(self):
        token_id = self._create_token_id()
        user_id = unicode(uuid.uuid4().hex)
        data = {'id': token_id, 'a': 'b',
                'user': {'id': user_id}}
        self.token_api.create_token(token_id, data)
        self.token_api.get_token(token_id)

    def test_list_tokens_unicode_user_id(self):
        user_id = unicode(uuid.uuid4().hex)
        self.token_api.list_tokens(user_id)

    def test_token_expire_timezone(self):

        @test_utils.timezone
        def _create_token(expire_time):
            token_id = uuid.uuid4().hex
            user_id = unicode(uuid.uuid4().hex)
            data = {'id': token_id, 'a': 'b', 'user': {'id': user_id},
                    'expires': expire_time
                    }
            self.token_api.create_token(token_id, data)
            return data

        for d in ['+0', '-11', '-8', '-5', '+5', '+8', '+14']:
            test_utils.TZ = 'UTC' + d
            expire_time = timeutils.utcnow() + \
                datetime.timedelta(minutes=1)
            data_in = _create_token(expire_time)
            data_get = None
            data_get = self.token_api.get_token(data_in['id'])

            self.assertIsNotNone(data_get, "TZ=%s" % test_utils.TZ)
            self.assertEquals(data_in['id'], data_get['id'],
                              "TZ=%s" % test_utils.TZ)

            expire_time_expired = timeutils.utcnow() + \
                datetime.timedelta(minutes=-1)
            data_in = _create_token(expire_time_expired)
            self.assertRaises(exception.TokenNotFound,
                              self.token_api.get_token, data_in['id'])
