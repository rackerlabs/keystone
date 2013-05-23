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

from keystone import config
from keystone.common import sql
from keystone import exception
from keystone.openstack.common import timeutils
from keystone.token import revocation

from keystone.token.backends import sql as token_sql

CONF = config.CONF


class Revocation(sql.Base, revocation.Driver):

    def __init__(self):
        if CONF.token.driver != 'keystone.token.backends.sql.Token':
            raise exception.ValidationError(_('The SQL Revocation Driver '
                                              'requires the SQL Token '
                                              'Driver.'))
        super(Revocation, self).__init__()

    def list_revoked_tokens(self):
        session = self.get_session()
        tokens = []
        now = timeutils.utcnow()
        query = session.query(token_sql.TokenModel)
        query = query.filter(token_sql.TokenModel.expires > now)
        token_references = query.filter_by(valid=False)
        for token_ref in token_references:
            record = {
                'id': token_ref['id'],
                'expires': token_ref['expires'],
            }
            tokens.append(record)
        return tokens

    def add_revoked_token(self, token_ref):
        pass

    def add_revoked_tokens(self, revoke_tokens_list, flush_all=False):
        pass

    def flush_expired_tokens(self):
        pass
