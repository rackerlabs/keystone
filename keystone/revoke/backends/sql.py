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
from keystone.common import sql
from keystone.common.sql import and_
from keystone.common.sql import or_
from keystone.common.sql import case
from keystone.common.sql import select
from keystone.models import revoke_model
from keystone.revoke.backends import base


class RevocationEvent(sql.ModelBase, sql.ModelDictMixin):
    __tablename__ = 'revocation_event'
    attributes = revoke_model.REVOKE_KEYS

    # The id field is not going to be exposed to the outside world.
    # It is, however, necessary for SQLAlchemy.
    id = sql.Column(sql.Integer, primary_key=True, nullable=False)
    domain_id = sql.Column(sql.String(64))
    project_id = sql.Column(sql.String(64))
    user_id = sql.Column(sql.String(64))
    role_id = sql.Column(sql.String(64))
    trust_id = sql.Column(sql.String(64))
    consumer_id = sql.Column(sql.String(64))
    access_token_id = sql.Column(sql.String(64))
    issued_before = sql.Column(sql.DateTime(), nullable=False)
    expires_at = sql.Column(sql.DateTime())
    revoked_at = sql.Column(sql.DateTime(), nullable=False, index=True)
    audit_id = sql.Column(sql.String(32))
    audit_chain_id = sql.Column(sql.String(32))


class Revoke(base.RevokeDriverV8):
    def _flush_batch_size(self, dialect):
        batch_size = 0
        if dialect == 'ibm_db_sa':
            # This functionality is limited to DB2, because
            # it is necessary to prevent the transaction log
            # from filling up, whereas at least some of the
            # other supported databases do not support update
            # queries with LIMIT subqueries nor do they appear
            # to require the use of such queries when deleting
            # large numbers of records at once.
            batch_size = 100
            # Limit of 100 is known to not fill a transaction log
            # of default maximum size while not significantly
            # impacting the performance of large token purges on
            # systems where the maximum transaction log size has
            # been increased beyond the default.
        return batch_size

    def _prune_expired_events(self):
        oldest = base.revoked_before_cutoff_time()

        with sql.session_for_write() as session:
            dialect = session.bind.dialect.name
            batch_size = self._flush_batch_size(dialect)
            if batch_size > 0:
                query = session.query(RevocationEvent.id)
                query = query.filter(RevocationEvent.revoked_at < oldest)
                query = query.limit(batch_size).subquery()
                delete_query = (session.query(RevocationEvent).
                                filter(RevocationEvent.id.in_(query)))
                while True:
                    rowcount = delete_query.delete(synchronize_session=False)
                    if rowcount == 0:
                        break
            else:
                query = session.query(RevocationEvent)
                query = query.filter(RevocationEvent.revoked_at < oldest)
                query.delete(synchronize_session=False)

            session.flush()

    def list_events(self, last_fetch=None):
        with sql.session_for_read() as session:
            query = session.query(RevocationEvent).order_by(
                RevocationEvent.revoked_at)

            if last_fetch:
                query = query.filter(RevocationEvent.revoked_at > last_fetch)

            events = [revoke_model.RevokeEvent(**e.to_dict()) for e in query]

            return events

    def revoke(self, event):
        kwargs = dict()
        for attr in revoke_model.REVOKE_KEYS:
            kwargs[attr] = getattr(event, attr)
        record = RevocationEvent(**kwargs)
        with sql.session_for_write() as session:
            session.add(record)
            self._prune_expired_events()

    def is_revoked(self, token_values):
        user_id_none = RevocationEvent.user_id.is_(None)
        user_id_filter = RevocationEvent.user_id.in_(
            [token_values[k] for k in ['user_id', 'trustor_id', 'trustee_id']])
        user_id_query = or_(user_id_none, user_id_filter)

        # See __init__ in RevokeEvent for the logic below
        # if self.domain_id and self.expires_at:
        #     # This is revoking a domain-scoped token.
        #     self.domain_scope_id = self.domain_id
        #     self.domain_id = None
        # else:
        #     # This is revoking all tokens for a domain.
        #     self.domain_scope_id = None

        expires_at_none = RevocationEvent.expires_at.is_(None)
        domain_id_none = RevocationEvent.domain_id.is_(None)

        domain_scope_id_none = or_(expires_at_none, domain_id_none)
        domain_scope_id_filter = RevocationEvent.domain_id.is_(token_values['assignment_domain_id'])
        domain_scope_id_query = or_(domain_scope_id_none,
                                    domain_scope_id_filter)

        domain_id_filter = RevocationEvent.domain_id.in_(
            [token_values[k]
             for k in ['identity_domain_id', 'assignment_domain_id']])
        domain_id_query = or_(~domain_scope_id_none, domain_id_filter)

        # If an event specifies an attribute name, but it does not  match,
        # the token is not revoked.

        project_id_none = RevocationEvent.project_id.is_(None)
        project_id_filter = RevocationEvent.project_id.is_(
            token_values['project_id'])
        project_id_query = or_(project_id_none, project_id_filter)

        expires_at_none = RevocationEvent.expires_at.is_(None)
        expires_at_filter = RevocationEvent.expires_at.is_(
            token_values['expires_at'])
        expires_at_query = or_(expires_at_none, expires_at_filter)

        trust_id_none = RevocationEvent.trust_id.is_(None)
        trust_id_filter = RevocationEvent.trust_id.is_(
            token_values['trust_id'])
        trust_id_query = or_(trust_id_none, trust_id_filter)


        consumer_id_none = RevocationEvent.consumer_id.is_(None)
        consumer_id_filter = RevocationEvent.consumer_id.is_(
            token_values['consumer_id'])
        consumer_id_query = or_(consumer_id_none, consumer_id_filter)

        access_token_id_none = RevocationEvent.access_token_id.is_(None)
        access_token_id_filter = RevocationEvent.access_token_id.is_(
            token_values['access_token_id'])
        access_token_id_query = or_(access_token_id_none,
                                     access_token_id_filter)

        audit_id_none = RevocationEvent.audit_id.is_(None)
        audit_id_filter = RevocationEvent.audit_id.is_(
            token_values['audit_id'])
        audit_id_query = or_(audit_id_none, audit_id_filter)

        audit_chain_id_none = RevocationEvent.audit_chain_id.is_(None)
        audit_chain_id_filter = RevocationEvent.audit_chain_id.is_(
            token_values['audit_chain_id'])
        audit_chain_id_query = or_(audit_chain_id_none,
                                   audit_chain_id_filter)

        # Check roles
        role_id_none = RevocationEvent.role_id.is_(None)
        role_id_filter = RevocationEvent.role_id.in_(token_values['roles']) if token_values.get('roles') else True
        role_id_query = or_(role_id_none, role_id_filter)

        # See __init__ in RevokeEvent for the logic below
        # if self.revoked_at is None:
        #     self.revoked_at = timeutils.utcnow()
        # if self.issued_before is None:
        #     self.issued_before = self.revoked_at
        issued_before_none = RevocationEvent.issued_before.is_(None)
        issued_before_filter = (
            RevocationEvent.issued_before >= token_values['issued_at'])
        issued_before_query = or_(issued_before_none, issued_before_filter)

        # TODO(samueldmq): First try to compare with revoked_at if it is not
        # None
        issued_before_revoked_at_filter = (
            datetime.datetime.utcnow() >= token_values['issued_at'])
        issued_before_revoked_at_query = or_(~issued_before_none,
                                             issued_before_revoked_at_filter)

        query = and_(user_id_query,
                     domain_scope_id_query,
                     domain_id_query,
                     project_id_query,
                     expires_at_query,
                     trust_id_query,
                     consumer_id_query,
                     access_token_id_query,
                     audit_id_query,
                     audit_chain_id_query,
                     role_id_query,
                     issued_before_query,
                     issued_before_revoked_at_query)

        with sql.session_for_read() as session:
            return session.query(query).first() is not None
