# Copyright 2012 OpenStack Foundation
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

import functools

from keystone.common import sql
from keystone import config
from keystone import exception
from keystone.openstack.common import log
from keystone.openstack.common import timeutils
from keystone import token


CONF = config.CONF
LOG = log.getLogger(__name__)


class TokenModel(sql.ModelBase, sql.DictBase):
    __tablename__ = 'token'
    attributes = ['id', 'expires', 'user_id', 'trust_id']
    id = sql.Column(sql.String(64), primary_key=True)
    expires = sql.Column(sql.DateTime(), default=None)
    extra = sql.Column(sql.JsonBlob())
    valid = sql.Column(sql.Boolean(), default=True, nullable=False)
    user_id = sql.Column(sql.String(64))
    trust_id = sql.Column(sql.String(64))
    __table_args__ = (
        sql.Index('ix_token_expires', 'expires'),
        sql.Index('ix_token_expires_valid', 'expires', 'valid')
    )


class Token(token.Driver):
    # Public interface
    def get_token(self, token_id):
        if token_id is None:
            raise exception.TokenNotFound(token_id=token_id)
        session = sql.get_session()
        token_ref = session.query(TokenModel).get(token_id)
        if not token_ref or not token_ref.valid:
            raise exception.TokenNotFound(token_id=token_id)
        return token_ref.to_dict()

    def create_token(self, token_id, data):
        data_copy = copy.deepcopy(data)
        if not data_copy.get('expires'):
            data_copy['expires'] = token.default_expire_time()
        if not data_copy.get('user_id'):
            data_copy['user_id'] = data_copy['user']['id']

        token_ref = TokenModel.from_dict(data_copy)
        token_ref.valid = True
        session = sql.get_session()
        with session.begin():
            session.add(token_ref)
        return token_ref.to_dict()

    def delete_token(self, token_id):
        session = sql.get_session()
        with session.begin():
            token_ref = session.query(TokenModel).get(token_id)
            if not token_ref or not token_ref.valid:
                raise exception.TokenNotFound(token_id=token_id)
            token_ref.valid = False

    def delete_tokens(self, user_id, tenant_id=None, trust_id=None,
                      consumer_id=None):
        """Deletes all tokens in one session

        The user_id will be ignored if the trust_id is specified. user_id
        will always be specified.
        If using a trust, the token's user_id is set to the trustee's user ID
        or the trustor's user ID, so will use trust_id to query the tokens.

        """
        session = sql.get_session()
        with session.begin():
            now = timeutils.utcnow()
            query = session.query(TokenModel)
            query = query.filter_by(valid=True)
            query = query.filter(TokenModel.expires > now)
            if trust_id:
                query = query.filter(TokenModel.trust_id == trust_id)
            else:
                query = query.filter(TokenModel.user_id == user_id)

            for token_ref in query.all():
                if tenant_id:
                    token_ref_dict = token_ref.to_dict()
                    if not self._tenant_matches(tenant_id, token_ref_dict):
                        continue
                if consumer_id:
                    token_ref_dict = token_ref.to_dict()
                    if not self._consumer_matches(consumer_id, token_ref_dict):
                        continue

                token_ref.valid = False

    def _tenant_matches(self, tenant_id, token_ref_dict):
        return ((tenant_id is None) or
                (token_ref_dict.get('tenant') and
                 token_ref_dict['tenant'].get('id') == tenant_id))

    def _consumer_matches(self, consumer_id, ref):
        if consumer_id is None:
            return True
        else:
            try:
                oauth = ref['token_data']['token'].get('OS-OAUTH1', {})
                return oauth and oauth['consumer_id'] == consumer_id
            except KeyError:
                return False

    def _list_tokens_for_trust(self, trust_id):
        session = sql.get_session()
        tokens = []
        now = timeutils.utcnow()
        query = session.query(TokenModel)
        query = query.filter(TokenModel.expires > now)
        query = query.filter(TokenModel.trust_id == trust_id)

        token_references = query.filter_by(valid=True)
        for token_ref in token_references:
            token_ref_dict = token_ref.to_dict()
            tokens.append(token_ref_dict['id'])
        return tokens

    def _list_tokens_for_user(self, user_id, tenant_id=None):
        session = sql.get_session()
        tokens = []
        now = timeutils.utcnow()
        query = session.query(TokenModel)
        query = query.filter(TokenModel.expires > now)
        query = query.filter(TokenModel.user_id == user_id)

        token_references = query.filter_by(valid=True)
        for token_ref in token_references:
            token_ref_dict = token_ref.to_dict()
            if self._tenant_matches(tenant_id, token_ref_dict):
                tokens.append(token_ref['id'])
        return tokens

    def _list_tokens_for_consumer(self, user_id, consumer_id):
        tokens = []
        session = sql.get_session()
        with session.begin():
            now = timeutils.utcnow()
            query = session.query(TokenModel)
            query = query.filter(TokenModel.expires > now)
            query = query.filter(TokenModel.user_id == user_id)
            token_references = query.filter_by(valid=True)

            for token_ref in token_references:
                token_ref_dict = token_ref.to_dict()
                if self._consumer_matches(consumer_id, token_ref_dict):
                    tokens.append(token_ref_dict['id'])
        return tokens

    def _list_tokens(self, user_id, tenant_id=None, trust_id=None,
                     consumer_id=None):
        if not CONF.token.revoke_by_id:
            return []
        if trust_id:
            return self._list_tokens_for_trust(trust_id)
        if consumer_id:
            return self._list_tokens_for_consumer(user_id, consumer_id)
        else:
            return self._list_tokens_for_user(user_id, tenant_id)

    def list_revoked_tokens(self):
        session = sql.get_session()
        tokens = []
        now = timeutils.utcnow()
        query = session.query(TokenModel.id, TokenModel.expires)
        query = query.filter(TokenModel.expires > now)
        token_references = query.filter_by(valid=False)
        for token_ref in token_references:
            record = {
                'id': token_ref[0],
                'expires': token_ref[1],
            }
            tokens.append(record)
        return tokens

    def _expiry_range_batched(self, session, upper_bound_func, batch_size):
        """Delete expired tokens in batches

        Return the timestamp of the next token that is `batch_size` rows from
        being the oldest expired token.
        """

        # If we're deleting in batches then we will get the next row that
        # is `batch_size` away from the oldest token.  We'll then delete
        # all the tokens up to the time on that token.  This may delete
        # slightly more tokens than the batch_size, but that should be ok
        # in almost all cases.  We're deleting in batches this way because
        # MySQL doesn't support DELETE queries with LIMIT subqueries and
        # SQLAlchemy doesn't support DELETE queries with direct LIMIT
        # clauses.
        LOG.info("Token expiration batch size: %d" % batch_size)
        query = session.query(TokenModel.expires)
        query = query.filter(TokenModel.expires < upper_bound_func())
        query = query.order_by(TokenModel.expires)
        query = query.offset(batch_size - 1)
        query = query.limit(1)
        while True:
            try:
                next_expiration = query.one()[0]
            except sql.NotFound:
                # There are less than `batch_size` rows remaining, so fall
                # through to the normal delete
                break
            yield next_expiration
        yield upper_bound_func()

    def _expiry_range_all(self, session, upper_bound_func):
        """Expires all tokens in one pass."""

        yield upper_bound_func()

    def _expiry_range_strategy(self, dialect):
        """Choose a token range expiration strategy

        Based on the DB dialect, select a expiry range function that is
        appropriate.
        """

        expiry_range_func = self._expiry_range_all
        if dialect == 'ibm_db_sa':
            # This functionality is limited to DB2, because
            # it is necessary to prevent the tranaction log
            # from filling up, whereas at least some of the
            # other supported databases do not support update
            # queries with LIMIT subqueries nor do they appear
            # to require the use of such queries when deleting
            # large numbers of records at once.
            expiry_range_func = functools.partial(self._expiry_range_batched,
                                                  batch_size=100)
            # Limit of 100 is known to not fill a transaction log
            # of default maximum size while not significantly
            # impacting the performance of large token purges on
            # systems where the maximum transaction log size has
            # been increased beyond the default.
        elif dialect == 'mysql':
            # This is also needed on MySQL when using Galera.  If token
            # expiration doesn't run for some time, then the change set may be
            # very large.  When using Galera replication, the maximum write set
            # size is fairly low by default and deleting a large number of
            # records at once will fail.
            expiry_range_func = functools.partial(self._expiry_range_batched,
                                                  batch_size=1000)
            # We want somewhat more than 100, since Galera replication delay is
            # at least RTT*2.  This can be a significant amount of time if
            # doing replication across a WAN.
        return expiry_range_func

    def flush_expired_tokens(self):
        session = sql.get_session()
        dialect = session.bind.dialect.name
        expiry_range_func = self._expiry_range_strategy(dialect)
        query = session.query(TokenModel.expires)
        total_removed = 0
        for expiry_time in expiry_range_func(session, timeutils.utcnow):
            delete_query = query.filter(TokenModel.expires <
                                        expiry_time)
            row_count = delete_query.delete(synchronize_session=False)
            LOG.info("Removed %d expired tokens", row_count)
            total_removed += row_count

        session.flush()
        LOG.info("Total expired tokens removed: %d", total_removed)
