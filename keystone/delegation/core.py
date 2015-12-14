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
import six

from keystone.common import dependency
from keystone.common import driver_hints
from keystone.common import manager
from keystone import exception
from keystone import notifications
from oslo_config import cfg
from oslo_log import log

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class BaseManager(manager.Manager):
    """Base for default pivot point for the Delegation backend.

    See :class:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """

    driver_namespace = 'keystone.delegation'

    def __init__(self):
        delegation_driver = CONF.delegation.driver
        super(BaseManager, self).__init__(delegation_driver)

    def validate_delegation(self, delegation):
        pass


@dependency.provider('delegation_api')
class Manager(manager.Manager):
    """Base for default pivot point for the Delegation backend.

    See :class:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """


@six.add_metaclass(abc.ABCMeta)
class DelegationDriverV8(object):
    """Driver interface for delegation low level management"""

    @abc.abstractmethod
    def derive_delegation(self, base_delegation,
                          agent, user, group, impersonation,
                          roles, project, domain,
                          strict_ancestry, sealed, executable):
        pass

    @abc.abstractmethod
    def update_delegation(self, delegation, grant_roles, revoke_roles):
        pass

    @abc.abstractmethod
    def revoke_delegation(self, delegation):
        pass

    @abc.abstractmethod
    def list_delegations(self, hints):
        pass

    @abc.abstractmethod
    def get_delegation(self, delegation):
        pass


class TrustManagaer(BaseManager):
    """Trust interface manager using delegation."""

    @staticmethod
    def _to_trust(delegation_ref):
        trust_ref = {
            'id': delegation_ref['id'],
            'trustor_user_id': delegation_ref['trustor_id'],
            'trustee_user_id': delegation_ref['user_chain'][-1],
            'project_id': delegation_ref['project_id'],
            'impersonation': delegation_ref['impersonation'],
            'expires_at': delegation_ref['expires_at'],
            'remaining_uses': delegation_ref['remaining_uses'],
            'deleted_at': delegation_ref['deleted_at'],
            'redelegated_trust_id': delegation_ref['delegation_chain'][-1],
            'redelegation_count': CONF.trust.max_redelegation_count,
            'roles': delegation_ref['roles']
        }
        return trust_ref

    @staticmethod
    def _from_trust_no_ancestry(trust_ref, roles):
        ref = {
            'id': trust_ref['id'],
            'trustor_id': trust_ref['trustor_user_id'],
            'project_id': trust_ref['project_id'],
            'impersonation': trust_ref['impersonation'],
            'expires_at': trust_ref['expires_at'],
            'deleted_at': trust_ref['deleted_at'],
            'roles': trust_ref.get('roles', roles)
        }
        return ref

    def get_trust(self, trust_id, deleted=False):
        delegation_ref = self.driver.get_delegation(delegation=trust_id)
        self.validate_delegation(delegation_ref)
        return self._to_trust(delegation_ref)

    def create_trust(self, trust_id, trust, roles, redelegated_trust=None,
                     initiator=None):
        if redelegated_trust:
            base_delegation = self.driver.get_trust(redelegated_trust['id'])
        else:
            base_delegation = None
        self.driver.derive_delegation(
            base_delegation=base_delegation,
            agent=trust['trustor_user_id'],
            user=trust['trustee_user_id'],
            group=None,
            impersonation=trust['impersonation'],
            roles=roles,
            project=trust['project_id'],
            domain=None,
            strict_ancestry=True,
            executable=True,
            sealed=trust.get('allow_redelegation', False))

        notifications.Audit.created(self._TRUST, trust_id, initiator=initiator)

    def delete_trust(self, trust_id, initiator=None):
        self.driver.revoke_delegation(delegation=trust_id)
        notifications.Audit.deleted(self._TRUST, trust_id, initiator)


@dependency.requires('role_api')
class AssignmentManager(BaseManager):
    """Assignment manager using delegation model"""

    def _to_assignments(self, delegations):
        for d in delegations:
            assignment_ref = {

            }
            yield assignment_ref

    @notifications.role_assignment('created')
    def create_grant(self, role_id, user_id=None, group_id=None,
                     domain_id=None, project_id=None,
                     inherited_to_projects=False, context=None):
        agent = context['user_id']
        base_delegation = None

        self.driver.derive_delegation(
            base_delegation=base_delegation,
            agent=agent,
            user=user_id,
            group=group_id,
            roles=[role_id],
            project=project_id,
            domain=domain_id,
            inherited_to_projects=inherited_to_projects)

    def get_grant(self, role_id, user_id=None, group_id=None,
                  domain_id=None, project_id=None,
                  inherited_to_projects=False, context=None):
        """Checks if a role has been granted on either a domain or project.

        :return: role
        """

        # TODO(amakarov): consider implied/hierarchical roles
        roles = self.list_grant_role_ids(user_id, group_id, domain_id,
                                         project_id, inherited_to_projects)
        if role_id not in roles:
            raise exception.RoleAssignmentNotFound(
                role_id=role_id, actor_id=user_id or group_id,
                target_id=domain_id or project_id)

        role_ref = self.role_api.get_role(role_id)
        return role_ref

    def list_grant_role_ids(self, user_id=None, group_id=None,
                            domain_id=None, project_id=None,
                            inherited_to_projects=False):
        # TODO(amakarov): consider project inheritance

        hints = driver_hints.Hints()
        hints.add_filter(name='user_id', value=user_id, case_sensitive=True)
        hints.add_filter(name='group_id', value=group_id, case_sensitive=True)
        hints.add_filter(name='domain_id', value=domain_id,
                         case_sensitive=True)
        hints.add_filter(name='project_id', value=project_id,
                         case_sensitive=True)
        hints.add_filter(name='inherited_to_projects',
                         value=inherited_to_projects)

        delegation_list = self.driver.list_delegations(hints)

        roles = six.reduce(lambda a, d: a | set(d.roles),
                           delegation_list, set())
        return list(roles)

    def list_user_ids_for_project(self, tenant_id):
        # TODO(amakarov): consider project inheritance
        hints = driver_hints.Hints()
        hints.add_filter(name='project_id', value=tenant_id,
                         case_sensitive=True)
        delegation_list = self.driver.list_delegations(hints)
        return [d['user_id'] for d in delegation_list]

    def list_role_assignments(self, role_id=None, user_id=None, group_id=None,
                              domain_id=None, project_id=None,
                              include_subtree=False, inherited=None,
                              effective=None):
        """List role assignments, honoring effective mode and provided filters.

        Returns a list of role assignments, where their attributes match the
        provided filters (role_id, user_id, group_id, domain_id, project_id and
        inherited). If include_subtree is True, then assignments on all
        descendants of the project specified by project_id are also included.
        The inherited filter defaults to None, meaning to get both
        non-inherited and inherited role assignments.

        If effective mode is specified, this means that rather than simply
        return the assignments that match the filters, any group or
        inheritance assignments will be expanded. Group assignments will
        become assignments for all the users in that group, and inherited
        assignments will be shown on the projects below the assignment point.
        Think of effective mode as being the list of assignments that actually
        affect a user, for example the roles that would be placed in a token.

        If OS-INHERIT extension is disabled or the used driver does not support
        inherited roles retrieval, inherited role assignments will be ignored.

        """
        if not CONF.os_inherit.enabled:
            if inherited:
                return []
            inherited = False

        subtree_ids = None
        if project_id and include_subtree:
            subtree_ids = (
                [x['id'] for x in
                    self.resource_api.list_projects_in_subtree(project_id)])

        # if effective:
        #     return self._list_effective_role_assignments(
        #         role_id, user_id, group_id, domain_id, project_id,
        #         subtree_ids, inherited)
        # else:
        #     return self._list_direct_role_assignments(
        #         role_id, user_id, group_id, domain_id, project_id,
        #         subtree_ids, inherited)
        pass

    def get_roles_for_user_and_project(self, user_id, tenant_id):
        """Get the roles associated with a user within given project.

        This includes roles directly assigned to the user on the
        project, as well as those by virtue of group membership or
        inheritance.

        :returns: a list of role ids.
        :raises keystone.exception.ProjectNotFound: If the project doesn't
            exist.

        """
        # self.resource_api.get_project(tenant_id)
        # assignment_list = self.list_role_assignments(
        #     user_id=user_id, project_id=tenant_id, effective=True)
        # # Use set() to process the list to remove any duplicates
        # return list(set([x['role_id'] for x in assignment_list]))

    def list_domains_for_groups(self, group_ids):
        # domain_ids = self.list_domain_ids_for_groups(group_ids)
        # return self.resource_api.list_domains_from_ids(domain_ids)
        pass

    # TODO(henry-nash): We might want to consider list limiting this at some
    # point in the future.
    def list_domains_for_user(self, user_id, hints=None):
        # # NOTE(henry-nash): In order to get a complete list of user domains,
        # # the driver will need to look at group assignments.  To avoid cross
        # # calling between the assignment and identity driver we get the group
        # # list here and pass it in. The rest of the detailed logic of listing
        # # projects for a user is pushed down into the driver to enable
        # # optimization with the various backend technologies (SQL, LDAP etc.).
        # group_ids = self._get_group_ids_for_user_id(user_id)
        # domain_ids = self.list_domain_ids_for_user(
        #     user_id, group_ids, hints or driver_hints.Hints())
        # return self.resource_api.list_domains_from_ids(domain_ids)
        pass

    def list_grants(self, user_id=None, group_id=None,
                    domain_id=None, project_id=None,
                    inherited_to_projects=False):
        # if domain_id:
        #     self.resource_api.get_domain(domain_id)
        # if project_id:
        #     self.resource_api.get_project(project_id)
        # grant_ids = self.list_grant_role_ids(
        #     user_id, group_id, domain_id, project_id, inherited_to_projects)
        # return self.role_api.list_roles_from_ids(grant_ids)
        pass

    def list_projects_for_groups(self, group_ids):
        # project_ids = (
        #     self.list_project_ids_for_groups(group_ids, driver_hints.Hints()))
        # if not CONF.os_inherit.enabled:
        #     return self.resource_api.list_projects_from_ids(project_ids)
        #
        # # os_inherit extension is enabled, so check to see if these groups have
        # # any inherited role assignment on: i) any domain, in which case we
        # # must add in all the projects in that domain; ii) any project, in
        # # which case we must add in all the subprojects under that project in
        # # the hierarchy.
        #
        # domain_ids = self.list_domain_ids_for_groups(group_ids, inherited=True)
        #
        # project_ids_from_domains = (
        #     self.resource_api.list_project_ids_from_domain_ids(domain_ids))
        #
        # parents_ids = self.list_project_ids_for_groups(group_ids,
        #                                                driver_hints.Hints(),
        #                                                inherited=True)
        #
        # subproject_ids = []
        # for parent_id in parents_ids:
        #     subtree = self.resource_api.list_projects_in_subtree(parent_id)
        #     subproject_ids += [subproject['id'] for subproject in subtree]
        #
        # return self.resource_api.list_projects_from_ids(
        #     list(set(project_ids + project_ids_from_domains + subproject_ids)))
        pass

    # TODO(henry-nash): We might want to consider list limiting this at some
    # point in the future.
    def list_projects_for_user(self, user_id, hints=None):
        # # NOTE(henry-nash): In order to get a complete list of user projects,
        # # the driver will need to look at group assignments.  To avoid cross
        # # calling between the assignment and identity driver we get the group
        # # list here and pass it in. The rest of the detailed logic of listing
        # # projects for a user is pushed down into the driver to enable
        # # optimization with the various backend technologies (SQL, LDAP etc.).
        #
        # group_ids = self._get_group_ids_for_user_id(user_id)
        # project_ids = self.list_project_ids_for_user(
        #     user_id, group_ids, hints or driver_hints.Hints())
        #
        # if not CONF.os_inherit.enabled:
        #     return self.resource_api.list_projects_from_ids(project_ids)
        #
        # # Inherited roles are enabled, so check to see if this user has any
        # # inherited role (direct or group) on any parent project, in which
        # # case we must add in all the projects in that parent's subtree.
        # project_ids = set(project_ids)
        # project_ids_inherited = self.list_project_ids_for_user(
        #     user_id, group_ids, hints or driver_hints.Hints(), inherited=True)
        # for proj_id in project_ids_inherited:
        #     project_ids.update(
        #         (x['id'] for x in
        #          self.resource_api.list_projects_in_subtree(proj_id)))
        #
        # # Now do the same for any domain inherited roles
        # domain_ids = self.list_domain_ids_for_user(
        #     user_id, group_ids, hints or driver_hints.Hints(),
        #     inherited=True)
        # project_ids.update(
        #     self.resource_api.list_project_ids_from_domain_ids(domain_ids))
        #
        # return self.resource_api.list_projects_from_ids(list(project_ids))
        pass

    def remove_role_from_user_and_project(self, user_id, tenant_id, role_id):
        # self._remove_role_from_user_and_project_adapter(
        #     role_id, user_id=user_id, project_id=tenant_id)
        pass

