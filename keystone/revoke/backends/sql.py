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

from keystone.common import sql
from keystone.models import revoke_model
from keystone.revoke.backends import base

from oslo_db import api as oslo_db_api
from sqlalchemy import and_, or_


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

    # As dolphm said, will add well defined keywords in the future. WIP
    def is_revoked(self, token_data):
        # Until I can drop some columns to make the token_data less mysterious
        # the for loop below is used to build dynamic OR/AND statements
        # depending on what token key/value pairs are in the dictionary
        R = RevocationEvent
        # remove empty key/val pairs
        token = {key: val for (key, val) in token_data.iteritems() if val}
        # The or statement for mapping user_id or trustor_id or trustee_id
        or1 = []
        # The or statement for mapping identity and assignemnt domain_id
        or2 = []
        # The and statement for all other one to one conditions
        and1 = []
        for key, value in token.iteritems():
            if key in ['user_id', 'trustor_id', 'trustee_id']:
                or1.append(or_(R.user_id.is_(None), R.user_id == value))

            elif key in ['identity_domain_id', 'assignment_domain_id']:
                or2.append(or_(R.domain_id.is_(None), R.domain_id == value))

            elif key == 'roles':
                # Since this is a list of values we check with 'in' instead
                and1.append(or_(R.role_id.is_(None), R.role_id in value))

            elif key == 'issued_at':
                and1.append(R.issued_before > value)

            else:
                and1.append(or_(getattr(R, key).is_(None),
                                getattr(R, key) == value))

        with sql.session_for_read() as session:
            # Make sure there is at least one revocation_event row in the table
            # otherwise this yields a DBError. So return False if is the case.
            rows = session.query(R).all()
            if len(rows) == 0:
                return False

            q = session.query(RevocationEvent)
            if or1:
                q = q.filter(or_(*or1))
            if or2:
                q = q.filter(or_(*or2))
            q = q.filter(and_(*and1))

            if not (session.query(q.exists()).scalar()):
                return False

        return True

    def list_events(self, last_fetch=None):
        with sql.session_for_read() as session:
            query = session.query(RevocationEvent).order_by(
                RevocationEvent.revoked_at)

            if last_fetch:
                query = query.filter(RevocationEvent.revoked_at > last_fetch)

            events = [revoke_model.RevokeEvent(**e.to_dict()) for e in query]

            return events

    @oslo_db_api.wrap_db_retry(retry_on_deadlock=True)
    def revoke(self, event):
        kwargs = dict()
        for attr in revoke_model.REVOKE_KEYS:
            kwargs[attr] = getattr(event, attr)
        record = RevocationEvent(**kwargs)
        with sql.session_for_write() as session:
            session.add(record)
            self._prune_expired_events()
