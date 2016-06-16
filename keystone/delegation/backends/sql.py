# Copyright 2016 OpenStack Foundation
#
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

from keystone.assignment.backends import base as assignment_base
from keystone.common import sql
from keystone.delegation.backends import sql_model as model
from keystone import exception
from keystone.i18n import _


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
