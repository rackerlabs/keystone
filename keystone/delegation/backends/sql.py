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

import abc
import time

from keystone import assignment
from keystone.common import sql
from keystone import exception
from keystone import trust
from keystone.contrib import oauth1
from oslo_config import cfg
from oslo_log import log
from oslo_utils import timeutils


CONF = cfg.CONF
LOG = log.getLogger(__name__)


MAXIMUM_CONSUME_ATTEMPTS = 10


class DelegationModel(sql.DictBase):

    __tablename__ = 'delegation'

    attributes = ['id',
                  'trustor_id',
                  'trustee_id',
                  'project_id',
                  'impersonation',
                  'origins',
                  'strict',
                  'deleted_at',
                  'expires_at',
                  'remaining_uses'
                  ]

    id = sql.Column(sql.String(64), primary_key=True)
    trustor_id = sql.Column(sql.String(64), nullable=False,)
    trustee_id = sql.Column(sql.String(64), nullable=False)
    project_id = sql.Column(sql.String(64))
    impersonation = sql.Column(sql.Boolean, nullable=False)
    origins = sql.Column(sql.Text, default='')
    strict = sql.Column(sql.Boolean, nullable=False, default=True)

    deleted_at = sql.Column(sql.DateTime)
    expires_at = sql.Column(sql.DateTime)
    remaining_uses = sql.Column(sql.Integer, nullable=True)


class RoleDelegationModel(sql.DictBase):
    """Many-to-many table between delegation and role"""

    __tablename__ = 'role_delegation'

    attributes = ['delegation_id', 'role_id']

    delegation_id = sql.Column(sql.String(64), nullable=False)
    role_id = sql.Column(sql.String(64), nullable=False)

    __table_args__ = (sql.PrimaryKeyConstraint('delegation_id', 'role_id'), )


class TrustDriver(trust.Driver):

    @staticmethod
    def _to_delegation(trust):
        return {
            'id': trust.get('id'),
            'trustor_id': trust.get('trustor_user_id'),
            'trustee_id': trust.get('trustee_user_id'),
            'project_id': trust.get('project_id'),
            'impersonation': trust.get('impersonation'),
            'deleted_at': trust.get('deleted_at'),
            'expires_at': trust.get('expires_at'),
            'remaining_uses': trust.get('remaining_uses')
        }

    @staticmethod
    def _to_trust(delegation):
        return{
            'id': delegation.get('id'),
            'trustor_user_id': delegation.get('trustor_id'),
            'trustee_user_id': delegation.get('trustee_id'),
            'project_id': delegation.get('project_id'),
            'impersonation': delegation.get('impersonation'),
            'expires_at': delegation.get('expires_at'),
            'remaining_uses': delegation.get('remaining_uses'),
            'deleted_at': delegation.get('deleted_at')
        }

    def create_trust(self, trust_id, trust, roles):
        """Create a new trust.

        :returns: a new trust
        """
        with sql.transaction() as session:
            ref = DelegationModel.from_dict(self._to_delegation(trust))
            ref['id'] = trust_id
            if ref.get('expires_at') and ref['expires_at'].tzinfo is not None:
                ref['expires_at'] = timeutils.normalize_time(ref['expires_at'])
            session.add(ref)
            added_roles = []
            for role in roles:
                trust_role = RoleDelegationModel()
                trust_role.delegation_id = trust_id
                trust_role.role_id = role['id']
                added_roles.append({'id': role['id']})
                session.add(trust_role)
        trust_dict = ref.to_dict()
        trust_dict['roles'] = added_roles
        return trust_dict

    def get_trust(self, trust_id, deleted=False):
        """Get a trust by the trust id.

        :param trust_id: the trust identifier
        :type trust_id: string
        :param deleted: return the trust even if it is deleted, expired, or
                        has no consumptions left
        :type deleted: bool
        """
        session = sql.get_session()
        query = session.query(DelegationModel).filter_by(id=trust_id)
        if not deleted:
            query = query.filter_by(deleted_at=None)
        ref = query.first()
        if ref is None:
            raise exception.TrustNotFound(trust_id=trust_id)
        if ref.expires_at is not None and not deleted:
            now = timeutils.utcnow()
            if now > ref.expires_at:
                raise exception.TrustNotFound(trust_id=trust_id)
        # Do not return trusts that can't be used anymore
        if ref.remaining_uses is not None and not deleted:
            if ref.remaining_uses <= 0:
                raise exception.TrustNotFound(trust_id=trust_id)
        trust_dict = self._to_trust(ref.to_dict())

        self._add_roles(trust_id, session, trust_dict)
        return trust_dict

    def list_trusts(self):
        session = sql.get_session()
        trusts = session.query(DelegationModel).filter_by(deleted_at=None)
        return [self._to_trust(trust_ref.to_dict()) for trust_ref in trusts]

    def list_trusts_for_trustee(self, trustee):
        session = sql.get_session()
        trusts = (session.query(DelegationModel).
                  filter_by(deleted_at=None).
                  filter_by(trustee_id=trustee))
        return [self._to_trust(trust_ref.to_dict()) for trust_ref in trusts]

    def list_trusts_for_trustor(self, trustor):
        session = sql.get_session()
        trusts = (session.query(DelegationModel).
                  filter_by(deleted_at=None).
                  filter_by(trustor_id=trustor))
        return [self._to_trust(trust_ref.to_dict()) for trust_ref in trusts]

    def delete_trust(self, trust_id):
        with sql.transaction() as session:
            trust_ref = session.query(DelegationModel).get(trust_id)
            if not trust_ref:
                raise exception.TrustNotFound(trust_id=trust_id)
            trust_ref.deleted_at = timeutils.utcnow()

    @sql.handle_conflicts(conflict_type='trust')
    def consume_use(self, trust_id):
        """Consume one use when a trust was created with a limitation on its
        uses, provided there are still uses available.

        :raises: keystone.exception.TrustUseLimitReached,
                 keystone.exception.TrustNotFound
        """
        for attempt in range(MAXIMUM_CONSUME_ATTEMPTS):
            with sql.transaction() as session:
                try:
                    query_result = (
                        session.query(DelegationModel.remaining_uses).
                        filter_by(id=trust_id, deleted_at=None).one()
                    )
                except sql.NotFound:
                    raise exception.TrustNotFound(trust_id=trust_id)

                remaining_uses = query_result.remaining_uses

                if remaining_uses is None:
                    # unlimited uses, do nothing
                    break
                elif remaining_uses > 0:
                    # NOTE(morganfainberg): use an optimistic locking method
                    # to ensure we only ever update a trust that has the
                    # expected number of remaining uses.
                    rows_affected = (
                        session.query(DelegationModel).
                        filter_by(id=trust_id, deleted_at=None,
                                  remaining_uses=remaining_uses).
                        update({'remaining_uses': (remaining_uses - 1)},
                               synchronize_session=False))
                    if rows_affected == 1:
                        # Successfully consumed a single limited-use trust.
                        # Since trust_id is the PK on the Trust table, there is
                        # no case we should match more than 1 row in the
                        # update. We either update 1 row or 0 rows.
                        break
                else:
                    raise exception.TrustUseLimitReached(trust_id=trust_id)
            # NOTE(morganfainberg): Ensure we have a yield point for eventlet
            # here. This should cost us nothing otherwise. This can be removed
            # if/when oslo_db cleanly handles yields on db calls.
            time.sleep(0)
        else:
            # NOTE(morganfainberg): In the case the for loop is not prematurely
            # broken out of, this else block is executed. This means the trust
            # was not unlimited nor was it consumed (we hit the maximum
            # iteration limit). This is just an indicator that we were unable
            # to get the optimistic lock rather than silently failing or
            # incorrectly indicating a trust was consumed.
            raise exception.TrustConsumeMaximumAttempt(trust_id=trust_id)


