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

from __future__ import absolute_import
import copy

import memcache

from keystone.common import utils
from keystone import config
from keystone import exception
from keystone.openstack.common import jsonutils
from keystone.openstack.common import timeutils
from keystone import token


CONF = config.CONF
config.register_str('servers', group='memcache', default='localhost:11211')
config.register_int('max_user_record_list_size', group='memcache', default=0)
config.register_int('max_compare_and_set_retry', group='memcache', default=16)


class Token(token.Driver):
    revocation_key = 'revocation-list'

    def __init__(self, client=None):
        self._memcache_client = client

    @property
    def client(self):
        return self._memcache_client or self._get_memcache_client()

    def _get_memcache_client(self):
        # NOTE(morganfainberg): The memcache client library for python is NOT
        # thread safe and should not be passed between threads. This is highly
        # specific to the cas() (compare and set) methods and the caching of
        # the previous value(s). It appears greenthread should ensure there is
        # a single data structure per spawned greenthread.
        memcache_servers = CONF.memcache.servers.split(',')
        self._memcache_client = memcache.Client(memcache_servers, debug=0,
                                                cache_cas=True)
        return self._memcache_client

    def _prefix_token_id(self, token_id):
        return 'token-%s' % token_id.encode('utf-8')

    def _prefix_user_id(self, user_id):
        return 'usertokens-%s' % user_id.encode('utf-8')

    def get_token(self, token_id):
        if token_id is None:
            raise exception.TokenNotFound(token_id='')
        ptk = self._prefix_token_id(token.unique_id(token_id))
        token_ref = self.client.get(ptk)
        if token_ref is None:
            raise exception.TokenNotFound(token_id=token_id)
        return token_ref

    def create_token(self, token_id, data):
        data_copy = copy.deepcopy(data)
        ptk = self._prefix_token_id(token.unique_id(token_id))
        if not data_copy.get('expires'):
            data_copy['expires'] = token.default_expire_time()
        if not data_copy.get('user_id'):
            data_copy['user_id'] = data_copy['user']['id']
        kwargs = {}
        if data_copy['expires'] is not None:
            expires_ts = utils.unixtime(data_copy['expires'])
            kwargs['time'] = expires_ts
        self.client.set(ptk, data_copy, **kwargs)
        if 'id' in data['user']:
            token_data = jsonutils.dumps(token_id)
            user_id = data['user']['id']
            user_key = self._prefix_user_id(user_id)
            if not self.client.append(user_key, ',%s' % token_data):
                if not self.client.add(user_key, token_data):
                    if not self.client.append(user_key, ',%s' % token_data):
                        self._flush_user_list(user_key, token_data=token_id)
        return copy.deepcopy(data_copy)

    def delete_token(self, token_id):
        # Test for existence
        token_copy = copy.deepcopy(self.get_token(token.unique_id(token_id)))
        ptk = self._prefix_token_id(token.unique_id(token_id))
        self.client.delete(ptk)
        return token_copy

    def batch_delete_tokens(self, token_list):
        deleted_tokens = []
        for token_id in token_list:
            try:
                deleted_tokens.append(self.delete_token(token_id))
            except exception.TokenNotFound:
                pass
        return deleted_tokens

    def _filter_list_and_cas(self, token_list_key, token_data=None):
        """
        If token_data is None, the list will be flushed of expired tokens.

        If token_data is provided, the list will be flushed of expired tokens
        and then the data will be appended to the new filtered list before
        the Compare-and-Set function in memcache is called.
        """
        is_revocation_list = False
        error_msg = _('Unable to add token user list.')

        cas_retry = 0
        filtered_list = []

        current_time = timeutils.normalize_time(
            timeutils.parse_isotime(timeutils.isotime()))

        # NOTE(morganfainberg): reset the cas cache to ensure we do not cause
        # memory bloat here.  CAS cache is not reset on it's own (ever)
        self.client.reset_cas()

        while cas_retry <= CONF.memcache.max_compare_and_set_retry:
            # NOTE(morganfainberg): cas or "compare and set" is a function of
            # memcache. It will return false if the value has changed since the
            # last call to client.gets(). This is the memcache supported method
            # of avoiding race conditions on set().  Memcache is already atomic
            # on the back-end and serializes operations.
            #
            # cas_retry is for tracking our iterations before we give up (in
            # case memcache is down or something horrible happens we don't
            # iterate forever trying to compare and set the new value.
            cas_retry += 1
            record = self.client.gets(token_list_key)

            if not record:
                break

            token_list = jsonutils.loads('[%s]' % record)
            for token_i in token_list:
                ptk = self._prefix_token_id(token.unique_id(token_i))
                token_ref = self.client.get(ptk)
                if not token_ref:
                    continue

                if 'expires' in token_ref:
                    if is_revocation_list:
                        expires_at = timeutils.parse_isotime(
                            token_ref['expires'])
                    else:
                        expires_at = token_ref['expires']
                    expiry = timeutils.normalize_time(expires_at)
                    if expiry < current_time:
                        continue
                filtered_list.append(jsonutils.dumps(token_i))
            if token_data is not None:
                filtered_list.append(jsonutils.dumps(token_data))
            if self.client.cas(token_list_key, ','.join(filtered_list)):
                return filtered_list
        raise exception.UnexpectedError(error_msg)

    def _flush_user_list(self, user_id, token_data=None):
        """
        Clean up the user-record-list of "expired" tokens using the memcache
        "cas" (compare and set) functionality.
        """
        user_key = self._prefix_user_id(user_id)
        return self._filter_list_and_cas(user_key, token_data=token_data)

    def list_tokens(self, user_id, tenant_id=None, trust_id=None):
        tokens = []
        user_key = self._prefix_user_id(user_id)
        user_record = self.client.get(user_key) or ""
        token_list = jsonutils.loads('[%s]' % user_record)
        if CONF.memcache.max_user_record_list_size > 0:
            # NOTE(morganfainberg): only keep the list smaller than the
            # max_user_record_list_size if the option is set.  Typically this
            # is only needed if there is a maximum list-size that is desired
            # that is less than the number that can fit in a memecache page.
            #
            # If this is set to 0, the flush will occur only if the list has
            # exceeded the memcache page-size and fails to append the token
            # unique id to the current list.
            if len(token_list) > CONF.memcache.max_user_record_list_size:
                token_list = self._flush_user_list(user_id)
        for token_id in token_list:
            ptk = self._prefix_token_id(token.unique_id(token_id))
            token_ref = self.client.get(ptk)
            if token_ref:
                if tenant_id is not None:
                    tenant = token_ref.get('tenant')
                    if not tenant:
                        continue
                    if tenant.get('id') != tenant_id:
                        continue
                if trust_id is not None:
                    trust = token_ref.get('trust_id')
                    if not trust:
                        continue
                    if trust != trust_id:
                        continue
                tokens.append(token_id)
        return tokens
