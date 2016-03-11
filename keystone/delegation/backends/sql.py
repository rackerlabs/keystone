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
import uuid

from oslo_context import context as oslo_context
from sqlalchemy import orm

from keystone.assignment.backends import sql as assignment_sql
from keystone.assignment import core as assignment_core
from keystone.common import config
from keystone.common import sql
from keystone import exception

CONF = config.CONF


def expiration_value():
    ttl = CONF.delegation.expiration
    if ttl:
        return datetime.datetime.now() + datetime.timedelta(ttl)
    else:
        return None


class RoleDelegationModel(sql.ModelBase):
    """Many-to-many table between delegation and role"""

    __tablename__ = 'role_delegation'

    attributes = ['id', 'delegation_id', 'role_id']

    id = sql.Column(sql.String(64), nullable=False, primary_key=True,
                    default=lambda: uuid.uuid4().hex)
    delegation_id = sql.Column(
        sql.String(64),
        sql.ForeignKey('delegation.id',
                       ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False)
    role_id = sql.Column(
        sql.String(64),
        sql.ForeignKey('role.id',
                       ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False)

    __table_args__ = (sql.UniqueConstraint('role_id', 'delegation_id',
                      name='duplicate_role_delegation_constraint'),)


class DelegationModel(sql.ModelBase, sql.DictBase):
    """Unified delegation model

    'trustor_id': the user considered the source of delegated rights
    'agent_id': the creator user of the delegation
    'impersonation': allowance for the delegate to impersonate the trustor
    'redelegated_id': parent link to track delegation ancestry chain
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
                  'agent_id',
                  'redelegated_id',
                  'impersonation',
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
    agent_id = sql.Column(sql.String(64), nullable=False)
    impersonation = sql.Column(sql.Boolean, nullable=False, default=False)
    redelegated_id = sql.Column(sql.String(64), nullable=True)

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

    role_links = orm.relationship(RoleDelegationModel)

    __table_args__ = (sql.UniqueConstraint(
                      'trustor_id', 'user_id', 'project_id',
                      'impersonation', 'expires_at',
                      name='duplicate_trust_delegation_constraint'),)


class AssignmentDriver(assignment_core.AssignmentDriverV9):

    def default_role_driver(self):
        return 'sql'

    def default_resource_driver(self):
        return 'sql'

    def create_grant(self, role_id, user_id=None, group_id=None,
                     domain_id=None, project_id=None,
                     inherited_to_projects=False):
        """Create delegation as an assignment"""
        # Detect the delegating agent
        context = oslo_context.get_current()
        agent_id = context.user

        # Find the best match for requested grant to be derived from
        with sql.session_for_read() as session:
            # Find delegations where agent is a trustee and scope matches
            # the requested
            # TODO(amakarov): decide who has the right to inherit a delegation
            # not being a trustee
            # TODO(amakarov): find all parents of the requested role
            roles = [role_id]
            q = (session.query(DelegationModel).join(RoleDelegationModel)
                 .filter(DelegationModel.id ==
                         RoleDelegationModel.delegation_id,
                         RoleDelegationModel.role_id.in_(roles),
                         DelegationModel.user_id == agent_id))

            # Deal with project inheritance and implied roles
            if domain_id is not None:
                # Domains are not inherited
                q = q.filter(DelegationModel.domain_id == domain_id)
            elif inherited_to_projects:
                # TODO(amakarov): find all ancestry of the requested project
                project_ancestry = [project_id]
                q = q.filter(
                    DelegationModel.project_id.in_(project_ancestry))
            else:
                # Project inheritance is not used
                q = q.filter(DelegationModel.project_id == project_id)

            candidates = [inst.to_dict() for inst in q.all()]

            # TODO(amakarov): choose the best matching candidate
            try:
                redelegated = candidates[0]
            except IndexError:
                # use a stub
                redelegated = {
                    'id': None,
                    'trustor_id': agent_id,
                    'impersonation': False,
                    'strict_ancestry': False
                }

        delegation = {
            'trustor_id': redelegated['trustor_id'],
            'agent_id': agent_id,
            'impersonation': redelegated['impersonation'],
            'redelegated_id': redelegated['id'],
            'strict_ancestry': redelegated['strict_ancestry'],
            'sealed': False,
            'executable': True,
            'inherited_to_projects': inherited_to_projects,
            'user_id': user_id,
            'group_id': group_id,
            'project_id': project_id,
            'domain_id': domain_id,
            'remaining_uses': None}
        delegation_ref = DelegationModel.from_dict(delegation)

        with sql.session_for_write() as session:
            session.add(delegation_ref)

        role_link_ref = RoleDelegationModel(delegation_id=delegation_ref.id,
                                            role_id=role_id)

        with sql.session_for_write() as session:
            session.add(role_link_ref)

    def list_grant_role_ids(self, user_id=None, group_id=None,
                            domain_id=None, project_id=None,
                            inherited_to_projects=False):
        with sql.session_for_read() as session:
            q = (session.query(DelegationModel.id, RoleDelegationModel.role_id)
                 .filter(DelegationModel.id ==
                         RoleDelegationModel.delegation_id))
            if user_id:
                q = q.filter(DelegationModel.user_id == user_id)
            elif group_id:
                q = q.filter(DelegationModel.group_id == group_id)
            if domain_id:
                q = q.filter(DelegationModel.domain_id == domain_id)
            elif project_id:
                q = q.filter(DelegationModel.project_id == project_id)
            q = q.filter(DelegationModel.inherited_to_projects ==
                         inherited_to_projects)
            return [x[1] for x in q.all()]

    def check_grant_role_id(self, role_id, user_id=None, group_id=None,
                            domain_id=None, project_id=None,
                            inherited_to_projects=False):
        with sql.session_for_read() as session:
            q = (session.query(DelegationModel, RoleDelegationModel)
                 .filter(DelegationModel.id ==
                         RoleDelegationModel.delegation_id,
                         RoleDelegationModel.role_id == role_id))
            if user_id:
                q = q.filter(DelegationModel.user_id == user_id)
            elif group_id:
                q = q.filter(DelegationModel.group_id == group_id)
            if domain_id:
                q = q.filter(DelegationModel.domain_id == domain_id)
            elif project_id:
                q = q.filter(DelegationModel.project_id == project_id)
            q = q.filter(DelegationModel.inherited_to_projects ==
                         inherited_to_projects)

            try:
                q.one()
            except sql.NotFound:
                actor_id = user_id or group_id
                target_id = domain_id or project_id
                raise exception.RoleAssignmentNotFound(role_id=role_id,
                                                       actor_id=actor_id,
                                                       target_id=target_id)

    def delete_grant(self, role_id, user_id=None, group_id=None,
                     domain_id=None, project_id=None,
                     inherited_to_projects=False):

        with sql.session_for_read() as session:
            q = (session.query(DelegationModel, RoleDelegationModel)
                 .filter(DelegationModel.id ==
                         RoleDelegationModel.delegation_id,
                         RoleDelegationModel.role_id == role_id))
            if user_id:
                q = q.filter(DelegationModel.user_id == user_id)
            elif group_id:
                q = q.filter(DelegationModel.group_id == group_id)
            if domain_id:
                q = q.filter(DelegationModel.domain_id == domain_id)
            elif project_id:
                q = q.filter(DelegationModel.project_id == project_id)
            q = q.filter(DelegationModel.inherited_to_projects ==
                         inherited_to_projects)

            results = list(q.all())
            if len(results):
                delegations, links = zip(*results)
            else:
                actor_id = user_id or group_id
                target_id = domain_id or project_id
                raise exception.RoleAssignmentNotFound(role_id=role_id,
                                                       actor_id=actor_id,
                                                       target_id=target_id)

        with sql.session_for_write() as session:
            [session.delete(l) for l in links]
            session.delete(delegations[0])

    def add_role_to_user_and_project(self, user_id, tenant_id, role_id):

        try:
            with sql.session_for_read() as session:
                q = (session.query(DelegationModel)
                     .filter(DelegationModel.id ==
                             RoleDelegationModel.delegation_id,
                             DelegationModel.user_id == user_id,
                             DelegationModel.project_id == tenant_id))
                try:
                    delegation_ref = q.one()
                except sql.NotFound:
                    delegation_ref = None

            if delegation_ref is not None:
                with sql.session_for_write() as session:
                    link_ref = RoleDelegationModel(
                        role_id=role_id, delegation_id=delegation_ref.id
                    )
                    session.add(link_ref)

        except sql.DBDuplicateEntry:
            msg = ('User %s already has role %s in tenant %s'
                   % (user_id, role_id, tenant_id))
            raise exception.Conflict(type='role grant', details=msg)

        if delegation_ref is None:
            # implicitly create a new delegation if needed
            self.create_grant(role_id, user_id=user_id, project_id=tenant_id)

    def remove_role_from_user_and_project(self, user_id, tenant_id, role_id):

        with sql.session_for_write() as session:
            q = session.query(RoleDelegationModel)
            q = q.filter(
                RoleDelegationModel.delegation_id.project_id == tenant_id,
                RoleDelegationModel.delegation_id.user_id == user_id,
                RoleDelegationModel.role_id == role_id)
            if q.delete() == 0:
                raise exception.RoleNotFound(message=_(
                    'Cannot remove role that has not been granted, %s') %
                    role_id)

    def list_role_assignments(self, role_id=None,
                              user_id=None, group_ids=None,
                              domain_id=None, project_ids=None,
                              inherited_to_projects=None):

        with sql.session_for_read() as session:
            q = (session.query(DelegationModel, RoleDelegationModel)
                 .filter(DelegationModel.id ==
                         RoleDelegationModel.delegation_id))

            if role_id:
                q = q.filter(
                    RoleDelegationModel.role_id == role_id)

            if group_ids:
                q = q.filter(DelegationModel.group_id.in_(group_ids))
            elif user_id:
                q = q.filter(DelegationModel.user_id == user_id)

            if project_ids:
                q = q.filter(
                    DelegationModel.project_id.in_(project_ids))
            elif domain_id:
                q = q.filter(DelegationModel.domain_id == domain_id)

            if inherited_to_projects is not None:
                q = q.filter(
                    DelegationModel.inherited_to_projects ==
                    inherited_to_projects)

            result = []
            for inst in q.all():
                entity = {
                    'type': (assignment_sql.AssignmentType
                             .calculate_type(inst[0].user_id,
                                             inst[0].group_id,
                                             inst[0].project_id,
                                             inst[0].domain_id)),
                    'actor_id': inst[0].user_id or inst[0].group_id,
                    'target_id': inst[0].project_id or inst[0].domain_id,
                    'role_id': inst[1].role_id,
                    'inherited': inst[0].inherited_to_projects,
                    'inherited_to_projects': inst[0].inherited_to_projects}

                inst[0].user_id and entity.update(user_id=inst[0].user_id)
                inst[0].group_id and entity.update(group_id=inst[0].group_id)
                inst[0].project_id and entity.update(
                    project_id=inst[0].project_id)
                inst[0].domain_id and entity.update(
                    domain_id=inst[0].domain_id)

                result.append(entity)

            return result

    def delete_project_assignments(self, project_id):
        with sql.session_for_write() as session:
            q = session.query(DelegationModel)
            q = q.filter_by(project_id=project_id)
            q.delete(False)

    def delete_role_assignments(self, role_id):
        with sql.session_for_write() as session:
            q = session.query(RoleDelegationModel).filter_by(role_id=role_id)
            q.delete(False)

    def delete_user_assignments(self, user_id):
        with sql.session_for_write() as session:
            q = session.query(DelegationModel)
            q = q.filter_by(user_id=user_id)
            q.delete(False)

    def delete_group_assignments(self, group_id):
        with sql.session_for_write() as session:
            q = session.query(DelegationModel)
            q = q.filter_by(group_id=group_id)
            q.delete(False)


class TrustDriver(object):

    def create_trust(self, trust_id, trust, roles):

        # Detect the delegating agent
        context = oslo_context.get_current()
        agent_id = context.user

        # Remember to check for the trust in the auth_token
        auth_token = context.auth_token
        auth_context = context.get('environment',
                                   {}).get('KEYSTONE_AUTH_CONTEXT', {})

        # Check if delegated via trust
        if auth_context.get('is_delegated_auth'):
            # Redelegation case
            src_trust_id = auth_context['trust_id']
            if not src_trust_id:
                raise exception.Forbidden(
                    _('Redelegation allowed for delegated by trust only'))

            redelegated_trust = self.trust_api.get_trust(src_trust_id)
        else:
            redelegated_trust = None

        # Find the best match for requested grant to be derived from
        with sql.session_for_read() as session:
            # Find delegations where agent is a trustee and scope matches
            # the requested
            # TBD(amakarov): decide who has the right to inherit a delegation
            # not being a trustee
            query = (session.query(DelegationModel,
                                   DelegationModel.role_links.role_id)
                     .filter(DelegationModel.user_id == agent_id))

            query = query.filter(
                DelegationModel.project_id == trust['project_id'])

            # TODO(amakarov): deal with implied roles somehow
            for instance in query.all():
                instance_roles = set(instance.role_links.role_id)

            roles = [role_id]
            query = query.filter(
                DelegationModel.role_links.role_id.in_(roles))

            candidates = [inst.to_dict() for inst in query]

            # TODO(amakarov): choose the best matching candidate
            try:
                redelegated = candidates[0]
            except IndexError:
                raise exception.NotFound(target="matching delegation")

        with sql.session_for_write() as session:
            delegation = {
                'trustor_id': trust['trustor_user_id'],
                'agent_id': agent_id,
                'redelegated_id': redelegated.id,
                'impersonation': trust['impersonation'],
                'strict_ancestry': True,
                'sealed': False,
                'executable': True,
                'inherited_to_projects': False,
                'user_id': trust['trustee_user_id'],
                'group_id': None,
                'project_id': trust['project_id'],
                'domain_id': None,
                'remaining_uses': trust['remaining_uses'],
                'expires_at': trust['expires_at']
            }

            ref = DelegationModel.from_dict(delegation)


            # ref = TrustModel.from_dict(trust)
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
