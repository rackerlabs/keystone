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

import contextlib
import uuid

from keystone.common import sql
from keystone import exception
from keystone.openstack.common import log
from keystone.openstack.common import timeutils
from keystone import trust


LOG = log.getLogger(__name__)


class TrustModel(sql.ModelBase, sql.DictBase):
    __tablename__ = 'trust'
    attributes = ['id', 'trustor_user_id', 'trustee_user_id',
                  'project_id', 'impersonation', 'expires_at',
                  'remaining_uses', 'lock']
    id = sql.Column(sql.String(64), primary_key=True)
    # user id of owner
    trustor_user_id = sql.Column(sql.String(64), nullable=False,)
    # user_id of user allowed to consume this preauth
    trustee_user_id = sql.Column(sql.String(64), nullable=False)
    project_id = sql.Column(sql.String(64))
    impersonation = sql.Column(sql.Boolean, nullable=False)
    deleted_at = sql.Column(sql.DateTime)
    expires_at = sql.Column(sql.DateTime)
    remaining_uses = sql.Column(sql.Integer, nullable=True)
    lock = sql.Column(sql.String(32), nullable=True)
    extra = sql.Column(sql.JsonBlob())


class TrustRole(sql.ModelBase):
    __tablename__ = 'trust_role'
    attributes = ['trust_id', 'role_id']
    trust_id = sql.Column(sql.String(64), primary_key=True, nullable=False)
    role_id = sql.Column(sql.String(64), primary_key=True, nullable=False)


@contextlib.contextmanager
def _lock_trust_record(trust_id):
    """Lock a specific trust record in the DB.

    This method should be used to lock a specific row in the DB with a
    unique identifier. This is a workaround for the known issue with
    MySQL+Galera and the 'SELECT ... FOR UPDATE' issues.

    Locking will only occur if the engine is MySQL, the trust is limited
    use, the trust is not deleted, and the trust is currently not locked.

    This context manager will yield a uuid lock_id if the dialect is MySQL,
    otherwise it will yield NoneType.

    :param trust_id: The Trust Identifier
    :return: None
    """

    session = sql.get_session()
    lock_info = None

    if session.bind.name == 'mysql':
        try:
            # NOTE(morganfainberg): Only need this if we are under mysql.
            lock_info = uuid.uuid4().hex

            with sql.transaction() as session:
                (session.query(TrustModel).
                 filter_by(deleted_at=None).
                 filter_by(id=trust_id).
                 filter_by(remaining_uses=None).
                 filter_by(lock=None).update({'lock': lock_info}))
        except sql.NotFound:
            # NOTE(morganfainberg): Either the trust is gone or already
            # locked. It is the responsibility of the method using the context
            # to figure out if the trust is locked or gone.
            pass

    # NOTE(morganfainberg): The lock_info can be used externally to
    # check that the context still holds the lock before performing any
    # updates.
    yield lock_info

    if lock_info:
        try:
            with sql.transaction() as session:
                (session.query(TrustModel).
                 filter_by(deleted_at=None).
                 filter_by(id=trust_id).
                 filter_by(lock=lock_info).update({'lock': None}))
        except sql.NotFound:
            # NOTE(morganfainberg): If we can't find the record to unlock
            # there is no reason we should be raising an error, the record
            # may have been deleted or the lock got mangled up.
            LOG.debug('Unable to find locked trust with id %(trust_id)s and '
                      'lock %(lock_id)s',
                      {'trust_id': trust_id, 'lock_id': lock_info})
            pass


class Trust(trust.Driver):
    @sql.handle_conflicts(conflict_type='trust')
    def create_trust(self, trust_id, trust, roles):
        with sql.transaction() as session:
            ref = TrustModel.from_dict(trust)
            ref['id'] = trust_id
            if ref.get('expires_at') and ref['expires_at'].tzinfo is not None:
                ref['expires_at'] = timeutils.normalize_time(ref['expires_at'])
            session.add(ref)
            added_roles = []
            for role in roles:
                trust_role = TrustRole()
                trust_role.trust_id = trust_id
                trust_role.role_id = role['id']
                added_roles.append({'id': role['id']})
                session.add(trust_role)
        trust_dict = ref.to_dict()
        trust_dict['roles'] = added_roles
        return trust_dict

    def _add_roles(self, trust_id, session, trust_dict):
        roles = []
        for role in session.query(TrustRole).filter_by(trust_id=trust_id):
            roles.append({'id': role.role_id})
        trust_dict['roles'] = roles

    @sql.handle_conflicts(conflict_type='trust')
    def consume_use(self, trust_id):
        with _lock_trust_record(trust_id) as lock_id:
            with sql.transaction() as session:
                if lock_id is None:
                    # NOTE(morganfainberg): lock_id will be None if the dialect
                    # is not mysql, meaning we can use `with_lockmode`.
                    ref = (session.query(TrustModel).
                           with_lockmode('update').
                           filter_by(deleted_at=None).
                           filter_by(id=trust_id).first())
                else:
                    ref = (session.query(TrustModel).
                           filter_by(deleted_at=None).
                           filter_by(id=trust_id).first())

                if ref is None:
                    raise exception.TrustNotFound(trust_id=trust_id)

                if ref.remaining_uses is None:
                    # unlimited uses, do nothing
                    pass
                elif lock_id is not None and ref.lock != lock_id:
                    raise exception.TrustLocked(trust_id=trust_id,
                                                expected_lock=lock_id,
                                                actual_lock=ref.lock)
                elif ref.remaining_uses > 0:
                    ref.remaining_uses -= 1
                else:
                    raise exception.TrustUseLimitReached(trust_id=trust_id)

    def get_trust(self, trust_id):
        session = sql.get_session()
        ref = (session.query(TrustModel).
               filter_by(deleted_at=None).
               filter_by(id=trust_id).first())
        if ref is None:
            return None
        if ref.expires_at is not None:
            now = timeutils.utcnow()
            if now > ref.expires_at:
                return None
        # Do not return trusts that can't be used anymore
        if ref.remaining_uses is not None:
            if ref.remaining_uses <= 0:
                return None
        trust_dict = ref.to_dict()

        self._add_roles(trust_id, session, trust_dict)
        return trust_dict

    @sql.handle_conflicts(conflict_type='trust')
    def list_trusts(self):
        session = sql.get_session()
        trusts = session.query(TrustModel).filter_by(deleted_at=None)
        return [trust_ref.to_dict() for trust_ref in trusts]

    @sql.handle_conflicts(conflict_type='trust')
    def list_trusts_for_trustee(self, trustee_user_id):
        session = sql.get_session()
        trusts = (session.query(TrustModel).
                  filter_by(deleted_at=None).
                  filter_by(trustee_user_id=trustee_user_id))
        return [trust_ref.to_dict() for trust_ref in trusts]

    @sql.handle_conflicts(conflict_type='trust')
    def list_trusts_for_trustor(self, trustor_user_id):
        session = sql.get_session()
        trusts = (session.query(TrustModel).
                  filter_by(deleted_at=None).
                  filter_by(trustor_user_id=trustor_user_id))
        return [trust_ref.to_dict() for trust_ref in trusts]

    @sql.handle_conflicts(conflict_type='trust')
    def delete_trust(self, trust_id):
        with sql.transaction() as session:
            trust_ref = session.query(TrustModel).get(trust_id)
            if not trust_ref:
                raise exception.TrustNotFound(trust_id=trust_id)
            trust_ref.deleted_at = timeutils.utcnow()
