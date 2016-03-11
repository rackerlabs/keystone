# Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import time

from oslo_context import context as oslo_context
from oslo_utils import timeutils

from keystone.assignment.backends import base as assignment_base
from keystone.common import sql
from keystone.delegation.backends import sql_model as model
from keystone import exception
from keystone.i18n import _
from keystone.trust.backends import base as trust_base

# The maximum number of iterations that will be attempted for optimistic
# locking on consuming a limited-use trust.
MAXIMUM_CONSUME_ATTEMPTS = 10


class AssignmentDriver(assignment_base.AssignmentDriverV9):

    def default_role_driver(self):
        return 'sql'

    def default_resource_driver(self):
        return 'sql'

    def create_grant(self, role_id, user_id=None, group_id=None,
                     domain_id=None, project_id=None,
                     inherited_to_projects=False,
                     agent_id=None, redelegated_id=None):
        """Create delegation as an assignment."""
        if redelegated_id:
            with sql.session_for_read() as session:
                redelegated = session.query(model.Delegation).get(
                    redelegated_id)
                redelegated_ref = redelegated.to_dict()
        else:
            redelegated_ref = {
                'trustor_id': None,
                'impersonation': False,
                'id': None,
                'strict_ancestry': False
            }

        delegation = {
            'trustor_id': redelegated_ref['trustor_id'],
            'agent_id': agent_id,
            'impersonation': redelegated_ref['impersonation'],
            'redelegated_id': redelegated_ref['id'],
            'strict_ancestry': redelegated_ref['strict_ancestry'],
            'sealed': False,
            'executable': True,
            'inherited_to_projects': inherited_to_projects,
            'user_id': user_id,
            'group_id': group_id,
            'project_id': project_id,
            'domain_id': domain_id,
            'remaining_uses': None}
        delegation_ref = model.Delegation.from_dict(delegation)

        with sql.session_for_write() as session:
            session.add(delegation_ref)

        role_link_ref = model.RoleDelegation(delegation_id=delegation_ref.id,
                                             role_id=role_id)

        with sql.session_for_write() as session:
            session.add(role_link_ref)

    def list_grant_role_ids(self, user_id=None, group_id=None,
                            domain_id=None, project_id=None,
                            inherited_to_projects=False):
        with sql.session_for_read() as session:
            q = (session.query(model.Delegation.id,
                               model.RoleDelegation.role_id)
                 .filter(model.Delegation.id ==
                         model.RoleDelegation.delegation_id))
            if user_id:
                q = q.filter(model.Delegation.user_id == user_id)
            elif group_id:
                q = q.filter(model.Delegation.group_id == group_id)
            if domain_id:
                q = q.filter(model.Delegation.domain_id == domain_id)
            elif project_id:
                q = q.filter(model.Delegation.project_id == project_id)
            q = q.filter(model.Delegation.inherited_to_projects ==
                         inherited_to_projects)
            return [x[1] for x in q.all()]

    def check_grant_role_id(self, role_id, user_id=None, group_id=None,
                            domain_id=None, project_id=None,
                            inherited_to_projects=False):
        with sql.session_for_read() as session:
            q = (session.query(model.Delegation, model.RoleDelegation)
                 .filter(model.Delegation.id ==
                         model.RoleDelegation.delegation_id,
                         model.RoleDelegation.role_id == role_id))
            if user_id:
                q = q.filter(model.Delegation.user_id == user_id)
            elif group_id:
                q = q.filter(model.Delegation.group_id == group_id)
            if domain_id:
                q = q.filter(model.Delegation.domain_id == domain_id)
            elif project_id:
                q = q.filter(model.Delegation.project_id == project_id)
            q = q.filter(model.Delegation.inherited_to_projects ==
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
        delegations, links = None, None

        with sql.session_for_read() as session:
            q = (session.query(model.Delegation, model.RoleDelegation)
                 .filter(model.Delegation.id ==
                         model.RoleDelegation.delegation_id,
                         model.RoleDelegation.role_id == role_id))
            if user_id:
                q = q.filter(model.Delegation.user_id == user_id)
            elif group_id:
                q = q.filter(model.Delegation.group_id == group_id)
            if domain_id:
                q = q.filter(model.Delegation.domain_id == domain_id)
            elif project_id:
                q = q.filter(model.Delegation.project_id == project_id)
            q = q.filter(model.Delegation.inherited_to_projects ==
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
        # This function is called by admin user only
        # so agent_id and redelegated_id should be None
        with sql.session_for_read() as session:
            q = (session.query(model.Delegation)
                 .filter(model.Delegation.project_id == tenant_id,
                         model.Delegation.user_id == user_id,
                         model.Delegation.agent_id.is_(None),
                         model.Delegation.redelegated_id.is_(None)))
            try:
                delegation_ref = q.one()
            except sql.NotFound:
                delegation_ref = None

        try:
            if delegation_ref is not None:
                with sql.session_for_write() as session:
                    link_ref = model.RoleDelegation(
                        role_id=role_id, delegation_id=delegation_ref.id
                    )
                    session.add(link_ref)
        except sql.DBDuplicateEntry:
            msg = ('User %s already has role %s in project %s'
                   % (user_id, role_id, tenant_id))
            raise exception.Conflict(type='role grant', details=msg)

        if delegation_ref is None:
            # implicitly create a new delegation if needed
            # assuming agent is admin

            self.create_grant(role_id, user_id=user_id, project_id=tenant_id,
                              agent_id=None, redelegated_id=None)

    def remove_role_from_user_and_project(self, user_id, tenant_id, role_id):

        with sql.session_for_write() as session:
            q = session.query(model.RoleDelegation)
            q = q.filter(
                model.RoleDelegation.delegation_id.project_id == tenant_id,
                model.RoleDelegation.delegation_id.user_id == user_id,
                model.RoleDelegation.role_id == role_id)
            if q.delete() == 0:
                raise exception.RoleNotFound(message=_(
                    'Cannot remove role that has not been granted, %s') %
                    role_id)

    @staticmethod
    def calculate_assignment_type(user_id, group_id, project_id, domain_id):
        if user_id:
            if project_id:
                return 'UserProject'
            if domain_id:
                return 'GroupProject'
        if group_id:
            if project_id:
                return 'UserDomain'
            if domain_id:
                return 'GroupDomain'
        # Invalid parameters combination
        raise exception.AssignmentTypeCalculationError(**locals())

    def list_role_assignments(self, role_id=None,
                              user_id=None, group_ids=None,
                              domain_id=None, project_ids=None,
                              inherited_to_projects=None):

        with sql.session_for_read() as session:
            q = (session.query(model.Delegation, model.RoleDelegation)
                 .filter(model.Delegation.id ==
                         model.RoleDelegation.delegation_id))

            if role_id:
                q = q.filter(
                    model.RoleDelegation.role_id == role_id)

            if group_ids:
                q = q.filter(model.Delegation.group_id.in_(group_ids))
            elif user_id:
                q = q.filter(model.Delegation.user_id == user_id)

            if project_ids:
                q = q.filter(
                    model.Delegation.project_id.in_(project_ids))
            elif domain_id:
                q = q.filter(model.Delegation.domain_id == domain_id)

            if inherited_to_projects is not None:
                q = q.filter(
                    model.Delegation.inherited_to_projects ==
                    inherited_to_projects)

            result = []
            for inst in q.all():
                delegation, role_link = inst
                assignment_type = self.calculate_assignment_type(
                    delegation.user_id, delegation.group_id,
                    delegation.project_id, delegation.domain_id
                )
                entity = {
                    'type': assignment_type,
                    'actor_id': delegation.user_id or delegation.group_id,
                    'target_id': delegation.project_id or delegation.domain_id,
                    'role_id': role_link.role_id,
                    'inherited': delegation.inherited_to_projects,
                    'inherited_to_projects': delegation.inherited_to_projects}

                if delegation.user_id:
                    entity.update(user_id=delegation.user_id)
                if delegation.group_id:
                    entity.update(group_id=delegation.group_id)
                if delegation.project_id:
                    entity.update(project_id=delegation.project_id)
                if delegation.domain_id:
                    entity.update(domain_id=delegation.domain_id)

                result.append(entity)

            return result

    def delete_project_assignments(self, project_id):
        with sql.session_for_write() as session:
            q = session.query(model.Delegation)
            q = q.filter_by(project_id=project_id)
            q.delete(False)

    def delete_role_assignments(self, role_id):
        with sql.session_for_write() as session:
            q = session.query(model.RoleDelegation).filter_by(role_id=role_id)
            q.delete(False)

    def delete_user_assignments(self, user_id):
        with sql.session_for_write() as session:
            q = session.query(model.Delegation)
            q = q.filter_by(user_id=user_id)
            q.delete(False)

    def delete_group_assignments(self, group_id):
        with sql.session_for_write() as session:
            q = session.query(model.Delegation)
            q = q.filter_by(group_id=group_id)
            q.delete(False)

    def delete_domain_assignments(self, domain_id):
        with sql.session_for_write() as session:
            q = session.query(model.Delegation)
            q = q.filter_by(domain_id=domain_id)
            q.delete(False)


class TrustDriver(trust_base.TrustDriverV8):

    @staticmethod
    def _format_trust_dict(delegation):
        with sql.session_for_read() as session:
            role_links = session.query(model.RoleDelegation).filter_by(
                delegation_id=delegation.id)
            return {'id': delegation.id,
                    'trustor_user_id': delegation.trustor_id,
                    'trustee_user_id': delegation.user_id,
                    'project_id': delegation.project_id,
                    'impersonation': delegation.impersonation,
                    'expires_at': delegation.expires_at,
                    'remaining_uses': delegation.remaining_uses,
                    'deleted_at': delegation.deleted_at,
                    'redelegated_trust_id': delegation.redelegated_id,
                    'redelegation_count': delegation.redelegation_count,
                    'roles': [{'id': r.role_id}
                              for r in role_links]}

    @sql.handle_conflicts(conflict_type='trust')
    def create_trust(self, trust_id, trust, roles):

        # Detect the delegating agent
        context = oslo_context.get_current()
        agent_id = context.user

        redelegated_id = trust.get('redelegated_trust_id')
        if redelegated_id:
            with sql.session_for_read() as session:
                session.query(model.Delegation).get(redelegated_id)

        with sql.session_for_write() as session:
            delegation = {
                'id': trust_id,
                'trustor_id': trust['trustor_user_id'],
                'agent_id': agent_id,
                'redelegated_id': redelegated_id,
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
                'expires_at': trust['expires_at'],
                'redelegation_count': trust['redelegation_count']
            }

            ref = model.Delegation.from_dict(delegation)

            if ref.get('expires_at') and ref['expires_at'].tzinfo is not None:
                ref['expires_at'] = timeutils.normalize_time(ref['expires_at'])
            session.add(ref)

        with sql.session_for_write() as session:
            for role in roles:
                role_link_ref = model.RoleDelegation(delegation_id=ref.id,
                                                     role_id=role['id'])
                session.add(role_link_ref)

        trust_dict = self._format_trust_dict(ref)
        return trust_dict

    def get_trust(self, trust_id, deleted=False):

        with sql.session_for_read() as session:
            query = session.query(model.Delegation).filter_by(id=trust_id)

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

            trust_dict = self._format_trust_dict(ref)
            return trust_dict

    @sql.handle_conflicts(conflict_type='trust')
    def consume_use(self, trust_id):

        for attempt in range(MAXIMUM_CONSUME_ATTEMPTS):
            with sql.session_for_write() as session:
                try:
                    query_result = (
                        session.query(model.Delegation.remaining_uses)
                        .filter_by(id=trust_id, deleted_at=None).one()
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
                        session.query(model.Delegation).
                        filter_by(id=trust_id).
                        filter_by(deleted_at=None).
                        filter_by(remaining_uses=remaining_uses).
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

    @sql.handle_conflicts(conflict_type='trust')
    def list_trusts(self):
        with sql.session_for_read() as session:
            delegations = session.query(model.Delegation).filter_by(
                deleted_at=None)
            return [self._format_trust_dict(d) for d in delegations]

    @sql.handle_conflicts(conflict_type='trust')
    def list_trusts_for_trustee(self, trustee_user_id):
        with sql.session_for_read() as session:
            delegations = (session.query(model.Delegation)
                           .filter_by(deleted_at=None,
                                      user_id=trustee_user_id))
            return [self._format_trust_dict(d) for d in delegations]

    @sql.handle_conflicts(conflict_type='trust')
    def list_trusts_for_trustor(self, trustor_user_id):
        with sql.session_for_read() as session:
            delegations = (session.query(model.Delegation)
                           .filter_by(deleted_at=None,
                                      trustor_id=trustor_user_id))
            return [self._format_trust_dict(d) for d in delegations]

    @sql.handle_conflicts(conflict_type='trust')
    def delete_trust(self, trust_id):
        with sql.session_for_write() as session:
            ref = session.query(model.Delegation).get(trust_id)
            if not ref:
                raise exception.TrustNotFound(trust_id=trust_id)
            ref.deleted_at = timeutils.utcnow()
