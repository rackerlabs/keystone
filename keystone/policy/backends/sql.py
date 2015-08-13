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

from keystone.common import sql
from keystone import exception
from keystone.policy.backends import rules


class PolicyModel(sql.ModelBase, sql.DictBase):
    __tablename__ = 'policy'
    attributes = ['id', 'blob', 'type']
    id = sql.Column(sql.String(64), primary_key=True)
    blob = sql.Column(sql.JsonBlob(), nullable=False)
    type = sql.Column(sql.String(255), nullable=False)
    extra = sql.Column(sql.JsonBlob())


class PolicyCacheModel(sql.ModelBase, sql.DictBase):
    __tablename__ = 'policy_cache'
    attributes = ['id', 'blob', 'type', 'valid_to']
    id = sql.Column(sql.String(64), primary_key=True)
    blob = sql.Column(sql.JsonBlob(), nullable=False)
    type = sql.Column(sql.String(255), nullable=False)
    extra = sql.Column(sql.JsonBlob())
    valid_to = sql.Column(sql.DateTime, nullable=False)


class Policy(rules.Policy):

    @sql.handle_conflicts(conflict_type='policy')
    def create_policy(self, policy_id, policy):
        session = sql.get_session()

        with session.begin():
            ref = PolicyModel.from_dict(policy)
            session.add(ref)

        return ref.to_dict()

    def list_policies(self):
        session = sql.get_session()

        refs = session.query(PolicyModel).all()
        return [ref.to_dict() for ref in refs]

    def _get_policy_cache(self, session, policy_id):
        """Private method to get a policy cache model object."""
        ref = session.query(PolicyCacheModel).get(policy_id)
        if not ref:
            raise exception.PolicyNotFound(policy_id=policy_id)
        return ref

    def get_policy_cache(self, policy_id):
        session = sql.get_session()

        return self._get_policy_cache(session, policy_id).to_dict()

    def _get_policy(self, session, policy_id):
        """Private method to get a policy model object (NOT a dictionary)."""
        ref = session.query(PolicyModel).get(policy_id)
        if not ref:
            raise exception.PolicyNotFound(policy_id=policy_id)
        return ref

    def get_policy(self, policy_id):
        session = sql.get_session()

        return self._get_policy(session, policy_id).to_dict()

    @sql.handle_conflicts(conflict_type='policy')
    def update_policy(self, policy_id, policy):
        session = sql.get_session()

        with session.begin():
            # Updates always occurs in the main table, caching mechanism will
            # apply the changes in the cache table
            ref = self._get_policy(session, policy_id)
            old_dict = ref.to_dict()
            old_dict.update(policy)
            new_policy = PolicyModel.from_dict(old_dict)
            ref.blob = new_policy.blob
            ref.type = new_policy.type
            ref.extra = new_policy.extra

        return ref.to_dict()

    def delete_policy(self, policy_id):
        session = sql.get_session()

        with session.begin():
            # Deletes always occurs in the main table, caching mechanism will
            # apply the changes in the cache table
            ref = self._get_policy(session, policy_id)
            session.delete(ref)

    def cache_policy(self, policy_id, valid_to):
        session = sql.get_session()

        with session.begin():
            try:
                ref_dict = self._get_policy(session, policy_id).to_dict()
            except exception.PolicyNotFound as exc:
                cached_ref = self._get_policy_cache(session, policy_id)
                session.delete(cached_ref)
                raise exc
            else:
                cached_ref_dict = ref_dict.copy()
                cached_ref_dict['valid_to'] = valid_to

                cached_ref = PolicyCacheModel.from_dict(cached_ref_dict)
                session.merge(cached_ref)

        return cached_ref.to_dict()
