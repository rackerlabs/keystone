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
from datetime import datetime
import uuid

from keystone.common import sql
from keystone.delegation import core
from keystone import exception
from oslo_config import cfg
from oslo_log import log


CONF = cfg.CONF
LOG = log.getLogger(__name__)


class DelegationModel(sql.DictBase):

    __tablename__ = 'delegation'

    attributes = ['id',
                  'trustor_id',
                  'impersonation',
                  'origins',
                  'strict',
                  'transitive',
                  'active',
                  'user_id',
                  'group_id',
                  'project_id',
                  'domain_id',
                  'deleted_at',
                  'expires_at',
                  'remaining_uses'
                  ]

    DELIMITER = '.'

    id = sql.Column(sql.String(64), primary_key=True,
                    default=lambda: uuid.uuid4().hex)

    # Identification
    trustor_id = sql.Column(sql.String(64), nullable=False)
    impersonation = sql.Column(sql.Boolean, nullable=False)
    origins = sql.Column(sql.Text)
    ancestors = sql.Column(sql.Text)

    # Constraints
    strict = sql.Column(sql.Boolean, nullable=False)
    transitive = sql.Column(sql.Boolean, nullable=False)
    active = sql.Column(sql.Boolean, nullable=False)

    # Scope
    user_id = sql.Column(sql.String(64))
    group_id = sql.Column(sql.String(64))
    project_id = sql.Column(sql.String(64))
    domain_id = sql.Column(sql.String(64))
    inherited = sql.Column(sql.Boolean, default=False, nullable=False)

    # Timestamps
    deleted_at = sql.Column(sql.DateTime)
    expires_at = sql.Column(sql.DateTime)

    # Specific fields, may be moved to "extra" blob
    remaining_uses = sql.Column(sql.Integer, nullable=True)


class RoleDelegationModel(sql.DictBase):
    """Many-to-many table between delegation and role"""

    __tablename__ = 'role_delegation'

    attributes = ['delegation_id', 'role_id']

    delegation_id = sql.Column(sql.String(64), nullable=False)
    role_id = sql.Column(sql.String(64), nullable=False)

    __table_args__ = (sql.PrimaryKeyConstraint('delegation_id', 'role_id'), )


class Driver(core.Driver):
    """Basic delegation driver implementing generic CRUD operation set"""

    def create(self, delegation_ref, agent_id, user_id, group_id, roles,
               strict, inherited_to_projects):
        """Inherited delegation created by agent"""
        hier = DelegationModel.from_dict(delegation_ref)
        hier.user_id = user_id
        hier.group_id = group_id
        hier.strict = strict
        hier.inherited = inherited_to_projects

        hier.expires_at = datetime.datetime.now() + CONF.delegation.expiration
        hier.origins = DelegationModel.DELIMITER.join([
            delegation_ref['origins'], delegation_ref.id])
        hier.ancestors += DelegationModel.DELIMITER.join([
            delegation_ref['ancestors'], agent_id])
        with sql.transaction() as session:
            session.add(hier)
            # TODO: validate roles
            for role_id in roles:
                session.add(RoleDelegationModel(
                    delegation_id=hier.id,
                    role_id=role_id
                ))

    def update(self, actor, project, grant_roles, revoke_roles):
        # TODO: identify the delegation
        # TODO: update roles
        pass

    def revoke(self, actor, project):
        # TODO: identify the delegation
        # TBD: mark as deleted or actually delete?
        pass

    def find(self, actor, project, inherited_to_projects):
        # TBD: filtering
        pass


class UnifiedDriver(object):
    """This is a draft of the delegation driver to replace existing ones

    Most probably it should be turned in several adapters that use the
    delegation driver.
    """

    # Assignment driver part

    def _role_to_dict(self, role_id, inherited):
        role_dict = {'id': role_id}
        if inherited:
            role_dict['inherited_to'] = 'projects'
        return role_dict

    def _roles_from_role_dicts(self, dict_list, inherited):
        role_list = []
        for d in dict_list:
            if ((not d.get('inherited_to') and not inherited) or
               (d.get('inherited_to') == 'projects' and inherited)):
                role_list.append(d['id'])
        return role_list

    def _add_role_to_role_dicts(self, role_id, inherited, dict_list,
                                allow_existing=True):
        # There is a difference in error semantics when trying to
        # assign a role that already exists between the coded v2 and v3
        # API calls.  v2 will error if the assignment already exists,
        # while v3 is silent. Setting the 'allow_existing' parameter
        # appropriately lets this call be used for both.
        role_set = set([frozenset(r.items()) for r in dict_list])
        key = frozenset(self._role_to_dict(role_id, inherited).items())
        if not allow_existing and key in role_set:
            raise KeyError
        role_set.add(key)
        return [dict(r) for r in role_set]

    def _remove_role_from_role_dicts(self, role_id, inherited, dict_list):
        role_set = set([frozenset(r.items()) for r in dict_list])
        role_set.remove(frozenset(self._role_to_dict(role_id,
                                                     inherited).items()))
        return [dict(r) for r in role_set]

    def _get_list_limit(self):
        return CONF.assignment.list_limit or CONF.list_limit

    @abc.abstractmethod
    def list_user_ids_for_project(self, tenant_id):
        """Lists all user IDs with a role assignment in the specified project.

        :returns: a list of user_ids or an empty set.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def add_role_to_user_and_project(self, user_id, tenant_id, role_id):
        """Add a role to a user within given tenant.

        :raises: keystone.exception.Conflict


        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def remove_role_from_user_and_project(self, user_id, tenant_id, role_id):
        """Remove a role from a user within given tenant.

        :raises: keystone.exception.RoleNotFound

        """
        raise exception.NotImplemented()  # pragma: no cover

    # assignment/grant crud

    @abc.abstractmethod
    def create_grant(self, role_id, user_id=None, group_id=None,
                     domain_id=None, project_id=None,
                     inherited_to_projects=False):
        """Creates a new assignment/grant.

        If the assignment is to a domain, then optionally it may be
        specified as inherited to owned projects (this requires
        the OS-INHERIT extension to be enabled).

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_grant_role_ids(self, user_id=None, group_id=None,
                            domain_id=None, project_id=None,
                            inherited_to_projects=False):
        """Lists role ids for assignments/grants."""

        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def check_grant_role_id(self, role_id, user_id=None, group_id=None,
                            domain_id=None, project_id=None,
                            inherited_to_projects=False):
        """Checks an assignment/grant role id.

        :raises: keystone.exception.RoleAssignmentNotFound
        :returns: None or raises an exception if grant not found

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def delete_grant(self, role_id, user_id=None, group_id=None,
                     domain_id=None, project_id=None,
                     inherited_to_projects=False):
        """Deletes assignments/grants.

        :raises: keystone.exception.RoleAssignmentNotFound

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_role_assignments(self):

        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_project_ids_for_user(self, user_id, group_ids, hints,
                                  inherited=False):
        """List all project ids associated with a given user.

        :param user_id: the user in question
        :param group_ids: the groups this user is a member of.  This list is
                          built in the Manager, so that the driver itself
                          does not have to call across to identity.
        :param hints: filter hints which the driver should
                      implement if at all possible.
        :param inherited: whether assignments marked as inherited should
                          be included.

        :returns: a list of project ids or an empty list.

        This method should not try and expand any inherited assignments,
        just report the projects that have the role for this user. The manager
        method is responsible for expanding out inherited assignments.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_project_ids_for_groups(self, group_ids, hints,
                                    inherited=False):
        """List project ids accessible to specified groups.

        :param group_ids: List of group ids.
        :param hints: filter hints which the driver should
                      implement if at all possible.
        :param inherited: whether assignments marked as inherited should
                          be included.
        :returns: List of project ids accessible to specified groups.

        This method should not try and expand any inherited assignments,
        just report the projects that have the role for this group. The manager
        method is responsible for expanding out inherited assignments.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_domain_ids_for_user(self, user_id, group_ids, hints,
                                 inherited=False):
        """List all domain ids associated with a given user.

        :param user_id: the user in question
        :param group_ids: the groups this user is a member of.  This list is
                          built in the Manager, so that the driver itself
                          does not have to call across to identity.
        :param hints: filter hints which the driver should
                      implement if at all possible.
        :param inherited: whether to return domain_ids that have inherited
                          assignments or not.

        :returns: a list of domain ids or an empty list.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_domain_ids_for_groups(self, group_ids, inherited=False):
        """List domain ids accessible to specified groups.

        :param group_ids: List of group ids.
        :param inherited: whether to return domain_ids that have inherited
                          assignments or not.
        :returns: List of domain ids accessible to specified groups.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_role_ids_for_groups_on_project(
            self, group_ids, project_id, project_domain_id, project_parents):
        """List the group role ids for a specific project.

        Supports the ``OS-INHERIT`` role inheritance from the project's domain
        if supported by the assignment driver.

        :param group_ids: list of group ids
        :type group_ids: list
        :param project_id: project identifier
        :type project_id: str
        :param project_domain_id: project's domain identifier
        :type project_domain_id: str
        :param project_parents: list of parent ids of this project
        :type project_parents: list
        :returns: list of role ids for the project
        :rtype: list
        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def list_role_ids_for_groups_on_domain(self, group_ids, domain_id):
        """List the group role ids for a specific domain.

        :param group_ids: list of group ids
        :type group_ids: list
        :param domain_id: domain identifier
        :type domain_id: str
        :returns: list of role ids for the project
        :rtype: list
        """
        raise exception.NotImplemented()

    @abc.abstractmethod
    def delete_project_assignments(self, project_id):
        """Deletes all assignments for a project.

        :raises: keystone.exception.ProjectNotFound

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def delete_role_assignments(self, role_id):
        """Deletes all assignments for a role."""

        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def delete_user_assignments(self, user_id):
        """Deletes all assignments for a user.

        :raises: keystone.exception.RoleNotFound

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def delete_group_assignments(self, group_id):
        """Deletes all assignments for a group.

        :raises: keystone.exception.RoleNotFound

        """
        raise exception.NotImplemented()  # pragma: no cover

    # Trust part

    @abc.abstractmethod
    def create_trust(self, trust_id, trust, roles):
        """Create a new trust.

        :returns: a new trust
        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def get_trust(self, trust_id, deleted=False):
        """Get a trust by the trust id.

        :param trust_id: the trust identifier
        :type trust_id: string
        :param deleted: return the trust even if it is deleted, expired, or
                        has no consumptions left
        :type deleted: bool
        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_trusts(self):
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_trusts_for_trustee(self, trustee):
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_trusts_for_trustor(self, trustor):
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def delete_trust(self, trust_id):
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def consume_use(self, trust_id):
        """Consume one use when a trust was created with a limitation on its
        uses, provided there are still uses available.

        :raises: keystone.exception.TrustUseLimitReached,
                 keystone.exception.TrustNotFound
        """
        raise exception.NotImplemented()  # pragma: no cover

    # OAuth part

    @abc.abstractmethod
    def create_consumer(self, consumer_ref):
        """Create consumer.

        :param consumer_ref: consumer ref with consumer name
        :type consumer_ref: dict
        :returns: consumer_ref

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def update_consumer(self, consumer_id, consumer_ref):
        """Update consumer.

        :param consumer_id: id of consumer to update
        :type consumer_id: string
        :param consumer_ref: new consumer ref with consumer name
        :type consumer_ref: dict
        :returns: consumer_ref

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_consumers(self):
        """List consumers.

        :returns: list of consumers

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def get_consumer(self, consumer_id):
        """Get consumer, returns the consumer id (key)
        and description.

        :param consumer_id: id of consumer to get
        :type consumer_id: string
        :returns: consumer_ref

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def get_consumer_with_secret(self, consumer_id):
        """Like get_consumer() but returned consumer_ref includes
        the consumer secret.

        Secrets should only be shared upon consumer creation; the
        consumer secret is required to verify incoming OAuth requests.

        :param consumer_id: id of consumer to get
        :type consumer_id: string
        :returns: consumer_ref

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def delete_consumer(self, consumer_id):
        """Delete consumer.

        :param consumer_id: id of consumer to get
        :type consumer_id: string
        :returns: None.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_access_tokens(self, user_id):
        """List access tokens.

        :param user_id: search for access tokens authorized by given user id
        :type user_id: string
        :returns: list of access tokens the user has authorized

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def delete_access_token(self, user_id, access_token_id):
        """Delete access token.

        :param user_id: authorizing user id
        :type user_id: string
        :param access_token_id: access token to delete
        :type access_token_id: string
        :returns: None

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def create_request_token(self, consumer_id, requested_project,
                             request_token_duration):
        """Create request token.

        :param consumer_id: the id of the consumer
        :type consumer_id: string
        :param requested_project_id: requested project id
        :type requested_project_id: string
        :param request_token_duration: duration of request token
        :type request_token_duration: string
        :returns: request_token_ref

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def get_request_token(self, request_token_id):
        """Get request token.

        :param request_token_id: the id of the request token
        :type request_token_id: string
        :returns: request_token_ref

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def get_access_token(self, access_token_id):
        """Get access token.

        :param access_token_id: the id of the access token
        :type access_token_id: string
        :returns: access_token_ref

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def authorize_request_token(self, request_id, user_id, role_ids):
        """Authorize request token.

        :param request_id: the id of the request token, to be authorized
        :type request_id: string
        :param user_id: the id of the authorizing user
        :type user_id: string
        :param role_ids: list of role ids to authorize
        :type role_ids: list
        :returns: verifier

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def create_access_token(self, request_id, access_token_duration):
        """Create access token.

        :param request_id: the id of the request token, to be deleted
        :type request_id: string
        :param access_token_duration: duration of an access token
        :type access_token_duration: string
        :returns: access_token_ref

        """
        raise exception.NotImplemented()  # pragma: no cover
