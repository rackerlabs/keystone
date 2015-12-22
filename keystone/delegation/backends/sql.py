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

import datetime
from oslo_utils import timeutils
import six
import uuid

from keystone.common import config
from keystone.common import sql
from keystone.delegation import core
from keystone import exception

CONF = config.CONF


def expiration_value():
    ttl = CONF.delegation.expiration
    if ttl:
        return datetime.datetime.now() + datetime.timedelta(ttl)
    else:
        return None


class DelegationModel(sql.ModelBase, sql.DictBase):
    """Unified delegation model

    'trustor_id': the user considered the source of delegated rights
    'impersonation': allowance for the delegate to impersonate the trustor
    'origins': ancestry chain of delegations
    'ancestors': ancestry chain of trustors
    'strict': whether to check if trustors are all enabled
    'transitive': indicates that rights can be delegated further
    'active': delegated rights can be used by the delegate
    'user_id': delegate user id empowered by the delegation
    'group_id': delegate group id which members are empowered by the delegation
    'project_id': scope of the delegation - the object of rights passed
    'domain_id': scope of the delegation - the object of rights passed
    'deleted_at': timestamp of delegation revocation
    'expires_at': timestamp of delegation expiration
    'remaining_uses': backwards compatibility field
    'inherited_to_projects': delegation applies to inherited projects
    """

    __tablename__ = 'delegation'

    attributes = ['id',
                  'trustor_id',
                  'impersonation',
                  'user_chain',
                  'delegation_chain',
                  'strict_ancestry',
                  'sealed',
                  'executable',
                  'inherited_to_projects',
                  'user_id',
                  'group_id',
                  'project_id',
                  'domain_id',
                  'deleted_at',
                  'expires_at',
                  'remaining_uses'
                  ]

    id = sql.Column(sql.String(64), primary_key=True,
                    default=lambda: uuid.uuid4().hex)

    # Identification
    trustor_id = sql.Column(sql.String(64), nullable=False)
    impersonation = sql.Column(sql.Boolean, nullable=False, default=False)
    user_chain = sql.Column(sql.MaterializedPathType, nullable=False,
                            default=[])
    delegation_chain = sql.Column(sql.MaterializedPathType, nullable=False,
                                  default=[])
    # Constraints
    strict_ancestry = sql.Column(sql.Boolean, nullable=False, default=False)
    sealed = sql.Column(sql.Boolean, nullable=False, default=True)
    executable = sql.Column(sql.Boolean, nullable=False, default=True)
    inherited_to_projects = sql.Column(sql.Boolean, nullable=False,
                                       default=False)

    # Scope
    user_id = sql.Column(sql.String(64))
    group_id = sql.Column(sql.String(64))
    project_id = sql.Column(sql.String(64))
    domain_id = sql.Column(sql.String(64))

    # Timestamps
    deleted_at = sql.Column(sql.DateTime)
    expires_at = sql.Column(sql.DateTime, default=expiration_value)

    # Specific fields, may be moved to "extra" blob
    remaining_uses = sql.Column(sql.Integer)

    extra = sql.Column(sql.JsonBlob())

    __table_args__ = (sql.UniqueConstraint(
                      'trustor_id', 'user_id', 'project_id',
                      'impersonation', 'expires_at',
                      name='duplicate_trust_delegation_constraint'),)

    @classmethod
    def to_instance(cls, delegation):
        if isinstance(delegation, cls):
            return delegation
        elif isinstance(delegation, six.string_types):
            session = sql.get_session()
            found = session.query(cls).get(delegation)
            if found is None:
                raise exception.NotFound(target=delegation)
            return found
        elif isinstance(delegation, dict):
            return cls.from_dict(delegation)
        else:
            raise sql.NotFound()


class RoleDelegationModel(sql.ModelBase):
    """Many-to-many table between delegation and role"""

    __tablename__ = 'role_delegation'

    attributes = ['delegation_id', 'role_id']

    delegation_id = sql.Column(sql.String(64), nullable=False)
    role_id = sql.Column(sql.String(64), nullable=False)

    __table_args__ = (sql.PrimaryKeyConstraint('delegation_id', 'role_id'), )

    @classmethod
    def get_delegation_roles(cls, delegation_id):
        session = sql.get_session()
        roles_query = session.query(cls).filter_by(
            delegation_id=delegation_id)
        return roles_query.all()


class Driver(core.DelegationDriverV8):

    def find_possible_bases(self, agent, domain, project, roles):
        # Try to find not sealed delegation to derive from.
        # We need a delegation where agent is the trustee,
        # resource match that requested,
        # and roles are a superset of the requested roles.
        session = sql.get_session()
        candidates = session.query(DelegationModel).filter_by(
            sealed=False, user_id=agent,
            project_id=project, domain_id=domain
        )
        matches = []
        requested_roles = set((r['id'] for r in roles))
        for candidate in candidates:
            candidate_roles = set([r['id'] for r in RoleDelegationModel.
                                   get_delegation_roles(candidate.id)])
            if requested_roles < candidate_roles:
                matches.append(candidate)
        return matches

    def parent_autodiscover(self, agent, domain, project,
                            roles, strict_ancestry):
        matches = self.find_possible_bases(agent, domain, project, roles)
        if len(matches) == 0:
            raise exception.NotFound(target="parent delegation")
        elif len(matches) == 1:
            base_delegation = matches[0]
        else:
            # Ok, what if several candidates are found?
            if strict_ancestry:
                raise exception.NotFound(target="single parent delegation")
            else:
                # If we don't care about delegation parents
                base_delegation = matches[0]
        return base_delegation

    @sql.handle_conflicts(conflict_type='delegation')
    def derive_delegation(self, id, base_delegation,
                          agent, user, group, impersonation,
                          roles, project, domain, inherited_to_projects,
                          strict_ancestry, sealed, executable, expires_at):
        session = sql.get_session()
        if base_delegation is None:
            try:
                base_delegation = self.parent_autodiscover(
                    agent, domain, project, roles, strict_ancestry)
            except exception.NotFound:
                trustor_id = agent
                user_chain = [agent]
                delegation_chain = []

        if base_delegation:
            try:
                base = DelegationModel.to_instance(base_delegation)
                # check sealed flag
                if base.sealed:
                    raise exception.TrustNotFound(trust_id=base.id)
                # check roles subset
                base_roles = [r['id'] for r in base.get_roles()]
                if any(1 for r in roles if r['id'] not in base_roles):
                    raise exception.Forbidden(
                        "Requested role cannot be granted")
                trustor_id = base['trustor_id']
                user_chain = base['user_chain'] + [agent]
                delegation_chain = base['delegation_chain'] + base['id']
            except sql.NotFound:
                raise exception.Forbidden("Base delegation not found")

        new_delegation_ref = {
            'id': id,
            'trustor_id': trustor_id,
            'impersonation': impersonation,
            'user_chain': user_chain,
            'delegation_chain': delegation_chain,
            'strict_ancestry': strict_ancestry,
            'sealed': sealed,
            'executable': executable,
            'inherited_to_projects': inherited_to_projects,
            'user_id': user,
            'group_id': group,
            'project_id': project,
            'domain_id': domain,
            'deleted_at': None,
            'expires_at': expires_at or timeutils.normalize_time(
                datetime.datetime.now() +
                datetime.timedelta(CONF.delegation.expiration)
            ),
            'remaining_uses': 1,
        }

        delegation = DelegationModel.from_dict(new_delegation_ref)
        new_delegation_ref['roles'] = []
        with session.begin():
            session.add(delegation)
            for role in roles:
                if isinstance(role, dict):
                    role = role['id']
                session.add(RoleDelegationModel(delegation_id=id,
                                                role_id=role))
                new_delegation_ref['roles'].append({'id': role})

        return new_delegation_ref

    def update_delegation(self, delegation, grant_roles, revoke_roles):
        pass

    def revoke_delegation(self, delegation):
        instance = DelegationModel.to_instance(delegation)
        session = sql.get_session()
        with session.begin():
            session.add(instance)
            instance.deleted_at = datetime.datetime.now()

    def list_delegations(self, hints=None, user=None, group=None,
                         project=None, domain=None, role=None,
                         expanded=False):
        # TODO(amakarov): Type autodiscover
        user_id = user
        group_id = group
        project_id = project
        domain_id = domain
        role_id = role

        filter_dict = {}
        user_id and filter_dict.update(user_id=user_id)
        group_id and filter_dict.update(group_id=group_id)
        project_id and filter_dict.update(project_id=project_id)
        domain_id and filter_dict.update(domain_id=domain_id)

        # TODO(amakarov): handle expanded flag
        session = sql.get_session()
        query = session.query(DelegationModel)
        if filter_dict:
            query = query.filter_by(**filter_dict)

        delegations = map(self.get_delegation, query.all())
        found = []
        for ref in delegations:
            if role_id is None:
                found.append(ref)
            else:
                for r in ref['roles']:
                    if r['id'] == role_id:
                        found.append(ref)
                        break
        return found

    def get_delegation(self, delegation):

        session = sql.get_session()
        if isinstance(delegation, six.string_types):
            delegation = session.query(DelegationModel).get(delegation)
            delegation_ref = delegation.to_dict()
        elif isinstance(delegation, DelegationModel):
            delegation_ref = delegation.to_dict()
        elif isinstance(delegation, dict):
            delegation_ref = delegation
        else:
            raise ValueError('Delegation type mismatch')

        roles = RoleDelegationModel.get_delegation_roles(delegation_ref['id'])
        delegation_ref['roles'] = [{'id': r.role_id} for r in roles]
        return delegation_ref
