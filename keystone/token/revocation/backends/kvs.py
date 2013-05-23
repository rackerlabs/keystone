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

from keystone.common import kvs
from keystone import exception
from keystone.openstack.common import timeutils
from keystone import token
from keystone.token import revocation


class Revocation(kvs.Base, revocation.Driver):
    revocation_key = 'revocation-list'

    def __init__(self):
        super(Revocation, self).__init__(db=kvs.DictKvs())

    def _build_revoked_token_list(self):
        now = timeutils.utcnow()
        revoked_token_list = []
        for token_key, ref, in self.db.items():
            if 'expires' in ref and ref['expires'] < now:
                try:
                    self.db.delete(token_key)
                except exception.TokenNotFound:
                    pass
                continue

            record = {}
            record['id'] = ref['id']
            record['expires'] = ref['expires']
            revoked_token_list.append(record)
        self.db.set(self.revocation_key, revoked_token_list)

    def _remove_all_entries(self):
        for token_key, ref in self.db.items():
            try:
                self.db.delete(token_key)
            except exception.TokenNotFound:
                pass

    def list_revoked_tokens(self):
        return self.db.get(self.revocation_key, [])

    def add_revoked_token(self, token_ref):
        token_id = token.unique_id(token_ref['id'])
        ref = copy.deepcopy(token_ref)
        self.db.set('revoked-token-%s' % token_id, ref)
        self._build_revoked_token_list()

    def add_revoked_tokens(self, revoke_tokens_list, flush_all=False):
        if flush_all:
            self._remove_all_entries()
        for token_ref in revoke_tokens_list:
            token_id = token.unique_id(token_ref['id'])
            ref = copy.deepcopy(token_ref)
            self.db.set('revoked-token-%s' % token_id, ref)
        self._build_revoked_token_list()

    def flush_expired_tokens(self):
        self._build_revoked_token_list()
