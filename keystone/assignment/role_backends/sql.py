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
from oslo_db import exception as db_exception
from sqlalchemy import and_

from keystone import assignment
from keystone.common import driver_hints
from keystone.common import sql
from keystone import exception

NULL_DOMAIN_ID = 'null'


class Role(assignment.RoleDriverV9):

    @sql.handle_conflicts(conflict_type='role')
    def create_role(self, role_id, role):

        def _ensure_domain_id_not_none(role):
            if 'domain_id' not in role or role['domain_id'] is None:
                new_role = role.copy()
                new_role['domain_id'] = NULL_DOMAIN_ID
                return new_role
            else:
                return role

        new_role = _ensure_domain_id_not_none(role)
        with sql.transaction() as session:
            ref = RoleTable.from_dict(new_role)
            session.add(ref)
            return ref.to_dict()

    @driver_hints.truncated
    def list_roles(self, hints):
        # If there is a filter on domain_id and the value is None, then to
        # ensure that the sql filtering works correctly, we need to patch
        # the value to be NULL_DOMAIN_ID. This is safe to do here since we
        # know we are able to satisfy any filter of this type in the call to
        # filter_limit_query() below, which will remove the filter from the
        # hints (hence ensuring our substitution is not exposed to the caller).
        for f in hints.filters:
            if (f['name'] == 'domain_id' and f['value'] is None):
                f['value'] = NULL_DOMAIN_ID

        with sql.transaction() as session:
            query = session.query(RoleTable)
            refs = sql.filter_limit_query(RoleTable, query, hints)
            return [ref.to_dict() for ref in refs]

    def list_roles_from_ids(self, ids):
        if not ids:
            return []
        else:
            with sql.transaction() as session:
                query = session.query(RoleTable)
                query = query.filter(RoleTable.id.in_(ids))
                role_refs = query.all()
                return [role_ref.to_dict() for role_ref in role_refs]

    def _get_role(self, session, role_id):
        ref = session.query(RoleTable).get(role_id)
        if ref is None:
            raise exception.RoleNotFound(role_id=role_id)
        return ref

    def get_role(self, role_id):
        with sql.transaction() as session:
            return self._get_role(session, role_id).to_dict()

    @sql.handle_conflicts(conflict_type='role')
    def update_role(self, role_id, role):

        def _ensure_domain_id_not_none(role):
            if 'domain_id' in role and role['domain_id'] is None:
                new_role = role.copy()
                new_role['domain_id'] = NULL_DOMAIN_ID
                return new_role
            else:
                return role

        update_role = _ensure_domain_id_not_none(role)
        with sql.transaction() as session:
            ref = self._get_role(session, role_id)
            old_dict = ref.to_dict()
            for k in update_role:
                old_dict[k] = update_role[k]
            if old_dict['domain_id'] is None:
                old_dict['domain_id'] = NULL_DOMAIN_ID
            new_role = RoleTable.from_dict(old_dict)
            for attr in RoleTable.attributes:
                if attr != 'id':
                    setattr(ref, attr, getattr(new_role, attr))
            ref.extra = new_role.extra
            return ref.to_dict()

    def delete_role(self, role_id):
        with sql.transaction() as session:
            ref = self._get_role(session, role_id)
            session.delete(ref)

    @sql.handle_conflicts(conflict_type='implied_role')
    def create_implied_role(self, prior_role_id, implied_role_id):
        with sql.transaction() as session:
            inference = {'prior_role_id': prior_role_id,
                         'implied_role_id': implied_role_id
                         }
            ref = ImpliedRoleTable.from_dict(inference)
            try:
                session.add(ref)
            except db_exception.DBReferenceError:
                # We don't know which role threw this.
                # Query each to trigger the exception.
                self._get_role(prior_role_id)
                self._get_role(implied_role_id)
            return ref.to_dict()

    def delete_implied_role(self, prior_role_id, implied_role_id):
        with sql.transaction() as session:
            (session.query(ImpliedRoleTable).filter(and_(
                ImpliedRoleTable.prior_role_id == prior_role_id,
                ImpliedRoleTable.implied_role_id == implied_role_id)).
             delete(synchronize_session='fetch'))

    def list_implied_roles(self, prior_role_id):
        with sql.transaction() as session:
            query = session.query(
                ImpliedRoleTable).filter(
                    ImpliedRoleTable.prior_role_id == prior_role_id)
            refs = query.all()
            return [ref.to_dict() for ref in refs]

    def list_role_inference_rules(self):
        with sql.transaction() as session:
            query = session.query(ImpliedRoleTable)
            refs = query.all()
            return [ref.to_dict() for ref in refs]

    def get_implied_role(self, prior_role_id, implied_role_id):
        with sql.transaction() as session:
            query = session.query(
                ImpliedRoleTable).filter(
                    ImpliedRoleTable.prior_role_id == prior_role_id).filter(
                        ImpliedRoleTable.implied_role_id == implied_role_id)
            ref = query.all()
            if len(ref) < 1:
                raise exception.ImpliedRoleNotFound(
                    prior_role_id=prior_role_id,
                    implied_role_id=implied_role_id)
            return ref[0].to_dict()


class ImpliedRoleTable(sql.ModelBase, sql.DictBase):
    @classmethod
    def from_dict(cls, dictionary):
        new_dictionary = dictionary.copy()
        return cls(**new_dictionary)

    def to_dict(self):
        """Return a dictionary with model's attributes."""
        d = dict()
        for attr in self.__class__.attributes:
            d[attr] = getattr(self, attr)
        return d

    __tablename__ = 'implied_role'
    attributes = ['prior_role_id', 'implied_role_id']
    prior_role_id = sql.Column(sql.String(64), sql.ForeignKey('role.id'),
                               primary_key=True)
    implied_role_id = sql.Column(sql.String(64), sql.ForeignKey('role.id'),
                                 primary_key=True)
    __table_args__ = ()


class RoleTable(sql.ModelBase, sql.DictBase):
    # NOTE(henry-nash): From the manager and above perspective, the domain_id
    # is nullable.  However, to ensure uniqueness in multi-process
    # configurations, it is better to still use the sql uniqueness constraint.
    # Since the support for a nullable component of a uniqueness constraint
    # across different sql databases is mixed, we instead store a special value
    # to represent null, as defined in NULL_DOMAIN_ID above.

    def to_dict(self, include_extra_dict=False):
        d = super(RoleTable, self).to_dict(
            include_extra_dict=include_extra_dict)
        if d['domain_id'] == NULL_DOMAIN_ID:
            d['domain_id'] = None
        return d

    __tablename__ = 'role'
    attributes = ['id', 'name', 'domain_id']
    id = sql.Column(sql.String(64), primary_key=True)
    name = sql.Column(sql.String(255), nullable=False)
    domain_id = sql.Column(sql.String(64), nullable=False,
                           server_default=NULL_DOMAIN_ID)
    extra = sql.Column(sql.JsonBlob())
    __table_args__ = (sql.UniqueConstraint('name', 'domain_id', ), {})
