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

import memcache
import uuid

from keystone.common import logging
from keystone import config
from keystone import exception
from keystone.openstack.common import jsonutils
from keystone.openstack.common import timeutils
from keystone.token import revocation


LOG = logging.getLogger(__name__)
CONF = config.CONF

config.register_int('maximum_revocation_list_pages', default=10,
                    group='memcache')

CONF.import_opt('servers', 'keystone.token.backends.memcache',
                group='memcache')
CONF.import_opt('max_compare_and_set_retry',
                'keystone.token.backends.memcache', group='memcache')


class Revocation(revocation.Driver):
    revocation_key = 'revocation-list'

    def __init__(self, client=None):
        self._memcache_client = client
        self._maximum_item_size = None
        self._revocation_page_list = []
        self._revocation_cache = []

    @property
    def client(self):
        return self._memcache_client or self._get_memcache_client()

    def _get_memcache_client(self):
        memcache_servers = CONF.memcache.servers.split(',')
        self._memcache_client = memcache.Client(memcache_servers, debug=0)
        self._maximum_item_size = None
        return self._memcache_client

    def _prefix_revocation_page(self, page_id):
        return 'revocation-page-%s' % page_id.encode('utf-8')

    def _get_revocation_list_from_pages(self):
        revocation_page_list = self._get_revocation_pages()

        if revocation_page_list != self._revocation_page_list:
            revoked_tokens = []

            if revocation_page_list:
                for key in revocation_page_list:
                    list_json = self.client.get(key)
                    if key:
                        page_list = jsonutils.loads(list_json)
                        revoked_tokens.extend(page_list)
            self._revocation_page_list = revocation_page_list
            self._revocation_cache = revoked_tokens

        return self._revocation_cache

    def _get_revocation_pages(self):
        return self.client.get(self.revocation_key) or []

    @property
    def max_item_size(self):
        if self._maximum_item_size is None:
            max_size = None
            settings = self.client.get_stats(stat_args='settings')
            for server in settings:
                if max_size is None or server[1]['item_max_size'] < max_size:
                    max_size = server[1]['item_max_size']
            self._maximum_item_size = max_size
        return self._maximum_item_size

    def _build_revocation_list(self, revoke_tokens_list, flush_all=False):
        cas_retry = 0

        # NOTE(morganfainberg): Cleanup CAS Cache when we call to ensure we
        # don't bloat our memory usage.
        self.client.reset_cas()

        while cas_retry <= CONF.memcache.max_compare_and_set_retry:
            cas_retry += 1

            new_revoked_tokens_list = []
            current_tokens = []
            now = timeutils.utcnow()

            # NOTE(morganfainberg): This call to gets is to set the CAS id
            # in the memcache client for the .cas() call later on.  It is not
            # relevant if this returns anything at this point.
            self.client.gets(self.revocation_key)

            original_pages = self._get_revocation_pages()
            if not flush_all:
                current_tokens = self._get_revocation_list_from_pages()

            for token in current_tokens:
                if 'expires' in token:
                    expire_time = timeutils.parse_isotime(token['expires'])
                    expiry = timeutils.normalize_time(expire_time)
                    if expiry < now:
                        continue
                new_revoked_tokens_list.append(token)
            new_revoked_tokens_list.extend(revoke_tokens_list)
            revoked_list_json = jsonutils.dumps(new_revoked_tokens_list)
            page_consumption = len(revoked_list_json) / self.max_item_size

            new_pages = {}

            if page_consumption > CONF.memcache.maximum_revocation_list_pages:
                error_msg = _('revocation-list would exceed maximum page '
                              'count of: %s') % page_consumption
                LOG.error(error_msg)
                raise exception.ValidationSizeError(error_msg)
            elif page_consumption > 1:
                page_count = 0
                num_revoked_tokens = len(new_revoked_tokens_list)
                increment = num_revoked_tokens / page_consumption

                while page_count < page_consumption:
                    page_key = self._prefix_revocation_page(uuid.uuid4().hex)

                    start_idx = page_count * increment
                    end_idx = page_count * increment + increment
                    if page_count == page_consumption:
                        # NOTE(morganfainberg): to capture the last element we
                        # need to encompass the last element in the list.
                        end_idx += 1

                    contents = new_revoked_tokens_list[start_idx:end_idx]
                    json_contents = jsonutils.dumps(contents)
                    new_pages[page_key] = json_contents
                    page_count += 1
            else:
                page_key = self._prefix_revocation_page(uuid.uuid4().hex)
                new_pages[page_key] = revoked_list_json

            if not self.client.set_multi(new_pages):
                continue

            if not self.client.cas(self.revocation_key, new_pages.keys()):
                self.client.delete_multi(new_pages.keys())
            else:
                self.client.delete_multi(original_pages)
                return

        raise exception.UnexpectedError(_('max_compare_and_set_retry exceeded '
                                          'building new revocation-list'))

    def add_revoked_token(self, token_ref):
        if not isinstance(token_ref, dict):
            raise exception.ValidationError(_('token_ref not type dict'))
        self.add_revoked_tokens(revoke_tokens_list=[token_ref])

    def add_revoked_tokens(self, revoke_tokens_list, flush_all=False):
        if not isinstance(revoke_tokens_list, list):
            raise exception.ValidationError(_('revoke_tokens_list not type '
                                              'list'))
        self._build_revocation_list(revoke_tokens_list=revoke_tokens_list,
                                    flush_all=flush_all)

    def list_revoked_tokens(self):
        return self._get_revocation_list_from_pages()

    def flush_expired_tokens(self):
        self._build_revocation_list(revoke_tokens_list=[])
