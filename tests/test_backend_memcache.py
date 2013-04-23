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

import copy
import datetime
import uuid

import memcache

from keystone.common import utils
from keystone.openstack.common import jsonutils
from keystone.openstack.common import timeutils
from keystone import test
from keystone import token
from keystone.token.backends import memcache as token_memcache

import test_backend


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

    def gets(self, key):
        """Call self.get() since we don't really do 'cas' here."""
        return self.get(key)

    def get(self, key):
        """Retrieves the value for a key or None."""
        self.check_key(key)
        obj = self.cache.get(key)
        now = utils.unixtime(timeutils.utcnow())
        if obj and (obj[1] == 0 or obj[1] > now):
            # NOTE(morganfainberg): This will behave more like memcache
            # actually does and will prevent modification of the passed in
            # reference from affecting the cached back-end data. This makes
            # tests a little easier to write.
            #
            # The back-end store should only change with an explicit
            # set/delete/append/etc
            data_copy = copy.deepcopy(obj[0])
            return data_copy

    def set(self, key, value, time=0):
        """Sets the value for a key."""
        self.check_key(key)
            # NOTE(morganfainberg): This will behave more like memcache
            # actually does and will prevent modification of the passed in
            # reference from affecting the cached back-end data. This makes
            # tests a little easier to write.
            #
            # The back-end store should only change with an explicit
            # set/delete/append/etc
        data_copy = copy.deepcopy(value)
        self.cache[key] = (data_copy, time)
        return True

    def cas(self, key, value, time=0, min_compress_len=0):
        """Call self.set() since we don't really do 'cas' here."""
        return self.set(key, value, time=time)

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

    def test_user_record_token_flush(self):
        valid_token_id = uuid.uuid4().hex
        expired_token_id = uuid.uuid4().hex
        user_id = unicode(uuid.uuid4().hex)

        expire_delta = datetime.timedelta(seconds=86400)

        valid_data = {'id': valid_token_id, 'a': 'b',
                      'user': {'id': user_id}}
        expired_data = {'id': expired_token_id, 'a': 'b',
                        'user': {'id': user_id},
                        'expires': (timeutils.utcnow() - expire_delta)}

        self.token_api.create_token(valid_token_id, valid_data)
        self.token_api.create_token(expired_token_id, expired_data)
        # NOTE(morganfainberg): Directly access the data cache since we need to
        # get expired tokens as well as valid tokens. token_api.list_tokens()
        # will not return any expired tokens in the list.
        user_key = self.token_api._prefix_user_id(user_id)
        user_record = self.token_api.client.get(user_key)
        user_token_list = jsonutils.loads('[%s]' % user_record)

        self.assertEquals(len(user_token_list), 2)

        self.token_api._flush_user_list_cas(user_id)
        flushed_user_record = self.token_api.client.get(user_key)
        flushed_list = jsonutils.loads('[%s]' % flushed_user_record)

        self.assertEquals(len(flushed_list), 1)
        self.assertIn(token.unique_id(valid_token_id), flushed_list)
        self.assertNotIn(token.unique_id(expired_token_id), flushed_list)

    def test_user_record_token_flush_append(self):
        valid_token_id = uuid.uuid4().hex
        expired_token_id = uuid.uuid4().hex
        new_token_id = uuid.uuid4().hex
        user_id = unicode(uuid.uuid4().hex)

        expire_delta = datetime.timedelta(seconds=86400)

        valid_data = {'id': valid_token_id, 'a': 'a',
                      'user': {'id': user_id}}
        expired_data = {'id': expired_token_id, 'a': 'b',
                        'user': {'id': user_id},
                        'expires': (timeutils.utcnow() - expire_delta)}
        new_token_data = {'id': new_token_id, 'a': 'c',
                          'user': {'id': user_id},
                          'expires': token.default_expire_time()}

        self.token_api.create_token(valid_token_id, valid_data)
        self.token_api.create_token(expired_token_id, expired_data)

        # NOTE(morganfainberg): Directly access the data cache since we need to
        # get expired tokens as well as valid tokens. token_api.list_tokens()
        # will not return any expired tokens in the list.
        user_key = self.token_api._prefix_user_id(user_id)
        user_record = self.token_api.client.get(user_key)
        user_token_list = jsonutils.loads('[%s]' % user_record)

        self.assertEquals(len(user_token_list), 2)
        ptk = self.token_api._prefix_token_id(token.unique_id(new_token_id))
        self.token_api.client.set(ptk, new_token_data)

        self.token_api._flush_user_list_cas(
            user_id, token_data=jsonutils.dumps(new_token_id))
        flushed_user_record = self.token_api.client.get(user_key)
        flushed_list = jsonutils.loads('[%s]' % flushed_user_record)

        self.assertEquals(len(flushed_list), 2)
        self.assertIn(token.unique_id(valid_token_id), flushed_list)
        self.assertIn(token.unique_id(new_token_id), flushed_list)
        self.assertNotIn(token.unique_id(expired_token_id), flushed_list)

    def test_revoked_token_flush(self):
        valid_token_id = uuid.uuid4().hex
        expired_token_id = uuid.uuid4().hex
        user_id = unicode(uuid.uuid4().hex)

        expire_delta = datetime.timedelta(seconds=86400)

        valid_data = {'id': valid_token_id, 'a': 'b',
                      'user': {'id': user_id},
                      'expires': token.default_expire_time()}
        expired_data = {'id': expired_token_id, 'a': 'b',
                        'user': {'id': user_id},
                        'expires': (timeutils.utcnow() - expire_delta)}

        self.token_api._add_to_revocation_list(valid_data)
        self.token_api._add_to_revocation_list(expired_data)
        # NOTE(morganfainberg): Unlike the user_record list getter, the method
        # token_api.list_revoked_tokens returns expired tokens as well as valid
        # tokens.
        self.assertEquals(len(self.token_api.list_revoked_tokens()), 2)

        self.token_api._flush_revocation_list_cas()
        revoked_list = [token.unique_id(t['id'])
                        for t in self.token_api.list_revoked_tokens()]

        self.assertEquals(len(revoked_list), 1)
        self.assertIn(token.unique_id(valid_token_id), revoked_list)
        self.assertNotIn(token.unique_id(expired_token_id), revoked_list)

    def test_max_user_record_list_size(self):
        tokens_generated = 0
        max_token_list_size = 5
        user_id = unicode(uuid.uuid4().hex)
        expired_token_id = uuid.uuid4().hex

        expire_delta = datetime.timedelta(seconds=86400)

        while tokens_generated < max_token_list_size:
            tokens_generated += 1

            token_id = uuid.uuid4().hex

            token_data = {'id': token_id, 'a': 'b',
                          'user': {'id': user_id}}

            self.token_api.create_token(token_id, token_data)

        expired_data = {'id': expired_token_id, 'a': 'b',
                        'user': {'id': user_id},
                        'expires': (timeutils.utcnow() - expire_delta)}
        self.token_api.create_token(expired_token_id, expired_data)
        tokens_generated += 1
        # NOTE(morganfainberg): Directly access the data cache since we need to
        # get expired tokens as well as valid tokens. token_api.list_tokens()
        # will not return any expired tokens in the list.
        user_key = self.token_api._prefix_user_id(user_id)
        user_record = self.token_api.client.get(user_key)
        user_token_list = jsonutils.loads('[%s]' % user_record)

        self.assertEquals(len(user_token_list), tokens_generated)
        self.token_api.list_tokens(user_id)
        flushed_user_record = self.token_api.client.get(user_key)
        flushed_list = jsonutils.loads('[%s]' % flushed_user_record)

        self.assertTrue(len(flushed_list) < len(user_token_list))
        self.assertNotIn(token.unique_id(expired_token_id), flushed_list)

    def max_revocation_list_size(self):
        tokens_generated = 0
        max_token_list_size = 5
        user_id = unicode(uuid.uuid4().hex)
        expired_token_id = uuid.uuid4().hex

        expire_delta = datetime.timedelta(seconds=86400)

        while tokens_generated < max_token_list_size:
            tokens_generated += 1

            token_id = uuid.uuid4().hex

            token_data = {'id': token_id, 'a': 'b',
                          'user': {'id': user_id}}

            self.token_api.create_token(token_id, token_data)
            self.token_api.delete_token(token_id)

        expired_data = {'id': expired_token_id, 'a': 'b',
                        'user': {'id': user_id},
                        'expires': (timeutils.utcnow() - expire_delta)}
        self.token_api._add_to_revocation_list(expired_data)
        tokens_generated += 1
        revocation_record = self.token_api.client.get(
            self.token_api.revocation_key)
        revoked_list = jsonutils.loads('[%s]' % self.token_api.client.get(
            revocation_record))

        self.assertEquals(len(revoked_list), tokens_generated)

        flushed_revoked_list = [token.unique_id(t['id'])
                                for t in self.token_api.list_revoked_tokens()]

        self.assertTrue(len(flushed_revoked_list) < len(revoked_list))
        self.assertNotIn(token.unique_id(expired_token_id),
                         flushed_revoked_list)
