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
config.register_int('max_revocation_list_size', group='memcache', default=0)
config.register_int('max_user_record_list_size', group='memcache', default=0)
config.register_int('max_cas_retry', group='memcache', default=16)
config.register_int('max_token_age', group='memcache', default=0)


class Token(token.Driver):
    revocation_key = 'revocation-list'

    def __init__(self, client=None):
        self._memcache_client = client

    @property
    def client(self):
        return self._memcache_client or self._get_memcache_client()

    def _get_memcache_client(self):
        # NOTE(morganfainberg): The memcache client library for python is NOT
        #                       thread safe, and should be instantiated per
        #                       thread if keystone moves to any form of
        #                       threading model.  This is highly specific
        #                       to the cas() (compare and set) methods and the
        #                       caching of the previous value(s).
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
        # NOTE(morganfainberg): "created_at" field is only used internally for
        #                       the flushing mechanisms and should never be
        #                       passed back out to anything else.
        token_ref.pop('created_at', None)
        return token_ref

    def create_token(self, token_id, data):
        data_copy = copy.deepcopy(data)
        ptk = self._prefix_token_id(token.unique_id(token_id))
        if not data_copy.get('expires'):
            data_copy['expires'] = token.default_expire_time()
        if not data_copy.get('user_id'):
            data_copy['user_id'] = data_copy['user']['id']
        data_copy['created_at'] = timeutils.utcnow()
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
                        if not self._flush_user_list_cas(user_key, token_data):
                            msg = _('Unable to add token user list.')
                            raise exception.UnexpectedError(msg)
        # NOTE(morganfainberg): "created_at" field is only used internally for
        #                       the flushing mechanisms and should never be
        #                       passed back out to anything else.
        data_copy.pop('created_at', None)
        return copy.deepcopy(data_copy)

    def _add_to_revocation_list(self, data):
        data_json = jsonutils.dumps(data)
        if not self.client.append(self.revocation_key, ',%s' % data_json):
            if not self.client.add(self.revocation_key, data_json):
                if not self.client.append(self.revocation_key,
                                          ',%s' % data_json):
                    if not self._flush_revocation_list_cas():
                        msg = _('Unable to add token to revocation list.')
                        raise exception.UnexpectedError(msg)

    def delete_token(self, token_id):
        # Test for existence
        data = self.get_token(token.unique_id(token_id))
        ptk = self._prefix_token_id(token.unique_id(token_id))
        result = self.client.delete(ptk)
        self._add_to_revocation_list(data)
        return result

    def _flush_user_list_cas(self, user_id, token_data=None):
        cas_retry = 0
        user_list_filtered = []
        user_key = self._prefix_user_id(user_id)
        current_time = timeutils.normalize_time(
            timeutils.parse_isotime(timeutils.isotime()))

        while cas_retry <= CONF.memcache.max_cas_retry:
            cas_retry += 1
            user_record = self.client.gets(user_key)

            if not user_record:
                return False

            user_token_list = jsonutils.loads('[%s]' % user_record)

            for token_id in user_token_list:
                ptk = self._prefix_token_id(token.unique_id(token_id))
                token_ref = self.client.get(ptk)
                if not token_ref:
                    continue
                if 'expires' in token_ref:
                    expiry = timeutils.normalize_time(token_ref['expires'])
                    if expiry < current_time:
                        continue
                if CONF.memcache.max_token_age:
                    # NOTE(morganfainberg): This is here to allow long-lived
                    #                       tokens to be artificially expired
                    #                       out if desired.  Default behavior
                    #                       is not to remove tokens in this
                    #                       manner.  An explicit delete is
                    #                       called here to avoid overflowing
                    #                       the revocation_list page.
                    if token_ref.get('created_at'):
                        token_age = current_time - token_ref['created_at']
                        token_age_seconds = token_age.total_seconds()
                        if token_age_seconds > CONF.memcache.max_token_age:
                            ptk = self._prefix_token_id(token_id)
                            self.client.delete(ptk)
                            continue
                user_list_filtered.append(jsonutils.dumps(token_id))
            if token_data is not None:
                user_list_filtered.append(token_data)

            if self.client.cas(user_key, ','.join(user_list_filtered)):
                return True
        return False

    def _flush_revocation_list_cas(self):
        cas_retry = 0

        while cas_retry <= CONF.memcache.max_cas_retry:
            cas_retry += 1
            tokens_filtered = []
            current_time = timeutils.normalize_time(
                timeutils.parse_isotime(timeutils.isotime()))
            revocation_record = self.client.gets(self.revocation_key)
            if not revocation_record:
                return False

            token_list = jsonutils.loads('[%s]' % revocation_record)

            for token_ref in token_list:
                if 'expires' in token_ref:
                    expires_at = timeutils.parse_isotime(token_ref['expires'])
                    expiry = timeutils.normalize_time(expires_at)
                    if expiry < current_time:
                        continue
                    tokens_filtered.append(jsonutils.dumps(token_ref))
            # NOTE(morganfainberg): We should do something here to handle
            #                       the case we are still over the max
            #                       list-size configured.  Do we remove the
            #                       oldest tokens from the list?  The closest
            #                       to expiration?
            if self.client.cas(self.revocation_key, ','.join(tokens_filtered)):
                return True
        return False

    def list_tokens(self, user_id, tenant_id=None, trust_id=None):
        tokens = []
        user_key = self._prefix_user_id(user_id)
        user_record = self.client.get(user_key) or ""
        token_list = jsonutils.loads('[%s]' % user_record)
        if CONF.memcache.max_user_record_list_size > 0:
            if len(token_list) > CONF.memcache.max_user_record_list_size:
                self._flush_user_list_cas(user_id)
                user_record = self.client.get(user_key) or ""
                token_list = jsonutils.loads('[%s]' % user_record)
        for token_id in token_list:
            ptk = self._prefix_token_id(token.unique_id(token_id))
            token_ref = self.client.get(ptk)
            if token_ref:
                # NOTE(morganfainberg): "created_at" field is only used
                #                       internally for the flushing mechanisms
                #                       and should never be passed back out to
                #                       anything else.
                token_ref.pop('created_at', None)
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

    def list_revoked_tokens(self):
        list_json = self.client.get(self.revocation_key)
        if list_json:
            revoked_list = jsonutils.loads('[%s]' % list_json)
            if CONF.memcache.max_revocation_list_size > 0:
                if len(revoked_list) > CONF.memcache.max_revocation_list_size:
                    self._flush_revocation_list_cas()
            return revoked_list
        return []
