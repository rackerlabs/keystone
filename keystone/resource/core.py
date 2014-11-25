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

"""Main entry point into the resource service."""

import abc

import six

from keystone import clean
from keystone.common import cache
from keystone.common import dependency
from keystone.common import driver_hints
from keystone.common import manager
from keystone import config
from keystone import exception
from keystone.i18n import _
from keystone import notifications
from keystone.openstack.common import log


CONF = config.CONF
LOG = log.getLogger(__name__)
SHOULD_CACHE = cache.should_cache_fn('resource')

# NOTE(blk-u): The config options are not available at import time.
EXPIRATION_TIME = lambda: CONF.resource.cache_time


def calc_default_domain():
    return {'description':
            (u'Owns users and tenants (i.e. projects)'
                ' available on Identity API v2.'),
            'enabled': True,
            'id': CONF.identity.default_domain_id,
            'name': u'Default'}


@dependency.provider('resource_api')
@dependency.optional('revoke_api')
@dependency.requires('assignment_api', 'credential_api', 'identity_api')
class Manager(manager.Manager):
    """Default pivot point for the resource backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """
    _PROJECT = 'project'

    def __init__(self):
        # If there is a specific driver specified for resource, then use it.
        # Otherwise retrieve the driver type from the identity driver.
        resource_driver = CONF.resource.driver

        if resource_driver is None:
            identity_driver = dependency.REGISTRY['identity_api'].driver
            resource_driver = identity_driver.default_resource_driver()

        super(Manager, self).__init__(resource_driver)

    @notifications.created(_PROJECT)
    def create_project(self, tenant_id, tenant):
        tenant = tenant.copy()
        tenant.setdefault('enabled', True)
        tenant['enabled'] = clean.project_enabled(tenant['enabled'])
        tenant.setdefault('description', '')
        ret = self.driver.create_project(tenant_id, tenant)
        if SHOULD_CACHE(ret):
            self.get_project.set(ret, self, tenant_id)
            self.get_project_by_name.set(ret, self, ret['name'],
                                         ret['domain_id'])
        return ret

    def assert_domain_enabled(self, domain_id, domain=None):
        """Assert the Domain is enabled.

        :raise AssertionError if domain is disabled.
        """
        if domain is None:
            domain = self.get_domain(domain_id)
        if not domain.get('enabled', True):
            raise AssertionError(_('Domain is disabled: %s') % domain_id)

    def assert_project_enabled(self, project_id, project=None):
        """Assert the project is enabled and its associated domain is enabled.

        :raise AssertionError if the project or domain is disabled.
        """
        if project is None:
            project = self.get_project(project_id)
        self.assert_domain_enabled(domain_id=project['domain_id'])
        if not project.get('enabled', True):
            raise AssertionError(_('Project is disabled: %s') % project_id)

    @notifications.disabled(_PROJECT, public=False)
    def _disable_project(self, project_id):
        """Emit a notification to the callback system project is been disabled.

        This method, and associated callback listeners, removes the need for
        making direct calls to other managers to take action (e.g. revoking
        project scoped tokens) when a project is disabled.

        :param project_id: project identifier
        :type project_id: string
        """
        pass

    @notifications.updated(_PROJECT)
    def update_project(self, tenant_id, tenant):
        original_tenant = self.driver.get_project(tenant_id)
        tenant = tenant.copy()
        if 'enabled' in tenant:
            tenant['enabled'] = clean.project_enabled(tenant['enabled'])
        if (original_tenant.get('enabled', True) and
                not tenant.get('enabled', True)):
            self._disable_project(tenant_id)
        ret = self.driver.update_project(tenant_id, tenant)
        self.get_project.invalidate(self, tenant_id)
        self.get_project_by_name.invalidate(self, original_tenant['name'],
                                            original_tenant['domain_id'])
        return ret

    @notifications.deleted(_PROJECT)
    def delete_project(self, tenant_id):
        project = self.driver.get_project(tenant_id)
        project_user_ids = (
            self.assignment_api.list_user_ids_for_project(tenant_id))
        for user_id in project_user_ids:
            payload = {'user_id': user_id, 'project_id': tenant_id}
            self._emit_invalidate_user_project_tokens_notification(payload)
        ret = self.driver.delete_project(tenant_id)
        self.assignment_api.delete_project_assignments(tenant_id)
        self.get_project.invalidate(self, tenant_id)
        self.get_project_by_name.invalidate(self, project['name'],
                                            project['domain_id'])
        self.credential_api.delete_credentials_for_project(tenant_id)
        return ret

    @cache.on_arguments(should_cache_fn=SHOULD_CACHE,
                        expiration_time=EXPIRATION_TIME)
    def get_domain(self, domain_id):
        return self.driver.get_domain(domain_id)

    @cache.on_arguments(should_cache_fn=SHOULD_CACHE,
                        expiration_time=EXPIRATION_TIME)
    def get_domain_by_name(self, domain_name):
        return self.driver.get_domain_by_name(domain_name)

    @notifications.created('domain')
    def create_domain(self, domain_id, domain):
        if (not self.identity_api.multiple_domains_supported and
                domain_id != CONF.identity.default_domain_id):
            raise exception.Forbidden(_('Multiple domains are not supported'))
        domain.setdefault('enabled', True)
        domain['enabled'] = clean.domain_enabled(domain['enabled'])
        ret = self.driver.create_domain(domain_id, domain)
        if SHOULD_CACHE(ret):
            self.get_domain.set(ret, self, domain_id)
            self.get_domain_by_name.set(ret, self, ret['name'])
        return ret

    @manager.response_truncated
    def list_domains(self, hints=None):
        return self.driver.list_domains(hints or driver_hints.Hints())

    @notifications.disabled('domain', public=False)
    def _disable_domain(self, domain_id):
        """Emit a notification to the callback system domain is been disabled.

        This method, and associated callback listeners, removes the need for
        making direct calls to other managers to take action (e.g. revoking
        domain scoped tokens) when a domain is disabled.

        :param domain_id: domain identifier
        :type domain_id: string
        """
        pass

    @notifications.updated('domain')
    def update_domain(self, domain_id, domain):
        original_domain = self.driver.get_domain(domain_id)
        if 'enabled' in domain:
            domain['enabled'] = clean.domain_enabled(domain['enabled'])
        ret = self.driver.update_domain(domain_id, domain)
        # disable owned users & projects when the API user specifically set
        #     enabled=False
        if (original_domain.get('enabled', True) and
                not domain.get('enabled', True)):
            self._disable_domain(domain_id)
        self.get_domain.invalidate(self, domain_id)
        self.get_domain_by_name.invalidate(self, original_domain['name'])
        return ret

    @notifications.deleted('domain')
    def delete_domain(self, domain_id):
        # explicitly forbid deleting the default domain (this should be a
        # carefully orchestrated manual process involving configuration
        # changes, etc)
        if domain_id == CONF.identity.default_domain_id:
            raise exception.ForbiddenAction(action=_('delete the default '
                                                     'domain'))

        domain = self.driver.get_domain(domain_id)

        # To help avoid inadvertent deletes, we insist that the domain
        # has been previously disabled.  This also prevents a user deleting
        # their own domain since, once it is disabled, they won't be able
        # to get a valid token to issue this delete.
        if domain['enabled']:
            raise exception.ForbiddenAction(
                action=_('cannot delete a domain that is enabled, '
                         'please disable it first.'))

        self._delete_domain_contents(domain_id)
        self.assignment_api.delete_domain_assignments(domain_id)
        self.driver.delete_domain(domain_id)
        self.get_domain.invalidate(self, domain_id)
        self.get_domain_by_name.invalidate(self, domain['name'])

    def _delete_domain_contents(self, domain_id):
        """Delete the contents of a domain.

        Before we delete a domain, we need to remove all the entities
        that are owned by it, i.e. Users, Groups & Projects. To do this we
        call the respective delete functions for these entities, which are
        themselves responsible for deleting any credentials and role grants
        associated with them as well as revoking any relevant tokens.

        The order we delete entities is also important since some types
        of backend may need to maintain referential integrity
        throughout, and many of the entities have relationship with each
        other. The following deletion order is therefore used:

        Projects: Reference user and groups for grants
        Groups: Reference users for membership and domains for grants
        Users: Reference domains for grants

        """
        user_refs = self.identity_api.list_users(domain_scope=domain_id)
        proj_refs = self.list_projects()
        group_refs = self.identity_api.list_groups(domain_scope=domain_id)

        # First delete the projects themselves
        for project in proj_refs:
            if project['domain_id'] == domain_id:
                try:
                    self.delete_project(project['id'])
                except exception.ProjectNotFound:
                    LOG.debug(('Project %(projectid)s not found when '
                               'deleting domain contents for %(domainid)s, '
                               'continuing with cleanup.'),
                              {'projectid': project['id'],
                               'domainid': domain_id})

        for group in group_refs:
            # Cleanup any existing groups.
            if group['domain_id'] == domain_id:
                try:
                    self.identity_api.delete_group(group['id'])
                except exception.GroupNotFound:
                    LOG.debug(('Group %(groupid)s not found when deleting '
                               'domain contents for %(domainid)s, continuing '
                               'with cleanup.'),
                              {'groupid': group['id'], 'domainid': domain_id})

        # And finally, delete the users themselves
        for user in user_refs:
            if user['domain_id'] == domain_id:
                try:
                    self.identity_api.delete_user(user['id'])
                except exception.UserNotFound:
                    LOG.debug(('User %(userid)s not found when '
                               'deleting domain contents for %(domainid)s, '
                               'continuing with cleanup.'),
                              {'userid': user['id'],
                               'domainid': domain_id})

    @manager.response_truncated
    def list_projects(self, hints=None):
        return self.driver.list_projects(hints or driver_hints.Hints())

    # NOTE(henry-nash): list_projects_in_domain is actually an internal method
    # and not exposed via the API.  Therefore there is no need to support
    # driver hints for it.
    def list_projects_in_domain(self, domain_id):
        return self.driver.list_projects_in_domain(domain_id)

    @cache.on_arguments(should_cache_fn=SHOULD_CACHE,
                        expiration_time=EXPIRATION_TIME)
    def get_project(self, project_id):
        return self.driver.get_project(project_id)

    @cache.on_arguments(should_cache_fn=SHOULD_CACHE,
                        expiration_time=EXPIRATION_TIME)
    def get_project_by_name(self, tenant_name, domain_id):
        return self.driver.get_project_by_name(tenant_name, domain_id)

    @cache.on_arguments(should_cache_fn=SHOULD_CACHE,
                        expiration_time=EXPIRATION_TIME)
    def get_role(self, role_id):
        return self.driver.get_role(role_id)

    @notifications.created('role')
    def create_role(self, role_id, role):
        ret = self.driver.create_role(role_id, role)
        if SHOULD_CACHE(ret):
            self.get_role.set(ret, self, role_id)
        return ret

    @manager.response_truncated
    def list_roles(self, hints=None):
        return self.driver.list_roles(hints or driver_hints.Hints())

    @notifications.updated('role')
    def update_role(self, role_id, role):
        ret = self.driver.update_role(role_id, role)
        self.get_role.invalidate(self, role_id)
        return ret

    @notifications.deleted('role')
    def delete_role(self, role_id):
        self.assignment_api.delete_tokens_for_role_assignments(role_id)
        self.assignment_api.delete_role_assignments(role_id)
        self.driver.delete_role(role_id)
        self.get_role.invalidate(self, role_id)

    @notifications.internal(
        notifications.INVALIDATE_USER_PROJECT_TOKEN_PERSISTENCE)
    def _emit_invalidate_user_project_tokens_notification(self, payload):
        # This notification's payload is a dict of user_id and
        # project_id so the token provider can invalidate the tokens
        # from persistence if persistence is enabled.
        pass


@six.add_metaclass(abc.ABCMeta)
class Driver(object):

    def _get_list_limit(self):
        return CONF.resource.list_limit or CONF.list_limit

    @abc.abstractmethod
    def get_project_by_name(self, tenant_name, domain_id):
        """Get a tenant by name.

        :returns: tenant_ref
        :raises: keystone.exception.ProjectNotFound

        """
        raise exception.NotImplemented()  # pragma: no cover

    # domain crud
    @abc.abstractmethod
    def create_domain(self, domain_id, domain):
        """Creates a new domain.

        :raises: keystone.exception.Conflict

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_domains(self, hints):
        """List domains in the system.

        :param hints: filter hints which the driver should
                      implement if at all possible.

        :returns: a list of domain_refs or an empty list.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_domains_from_ids(self, domain_ids):
        """List domains for the provided list of ids.

        :param domain_ids: list of ids

        :returns: a list of domain_refs.

        This method is used internally by the assignment manager to bulk read
        a set of domains given their ids.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def get_domain(self, domain_id):
        """Get a domain by ID.

        :returns: domain_ref
        :raises: keystone.exception.DomainNotFound

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def get_domain_by_name(self, domain_name):
        """Get a domain by name.

        :returns: domain_ref
        :raises: keystone.exception.DomainNotFound

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def update_domain(self, domain_id, domain):
        """Updates an existing domain.

        :raises: keystone.exception.DomainNotFound,
                 keystone.exception.Conflict

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def delete_domain(self, domain_id):
        """Deletes an existing domain.

        :raises: keystone.exception.DomainNotFound

        """
        raise exception.NotImplemented()  # pragma: no cover

    # project crud
    @abc.abstractmethod
    def create_project(self, project_id, project):
        """Creates a new project.

        :raises: keystone.exception.Conflict

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_projects(self, hints):
        """List projects in the system.

        :param hints: filter hints which the driver should
                      implement if at all possible.

        :returns: a list of project_refs or an empty list.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_projects_in_domain(self, domain_id):
        """List projects in the domain.

        :param domain_id: the driver MUST only return projects
                          within this domain.

        :returns: a list of project_refs or an empty list.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_projects_from_ids(self, project_ids):
        """List projects for the provided list of ids.

        :param project_ids: list of ids

        :returns: a list of project refs.

        This method is used internally by the assignment manager to bulk read
        a set of projects given their ids.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_project_ids_from_domain_ids(self, domain_ids):
        """List project ids for the provided list of domain ids.

        :param domain_ids: list of domain ids

        :returns: a list of project ids owned by the specified domain ids.

        This method is used internally by the assignment manager to bulk read
        a set of project ids given a list of domain ids.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def get_project(self, project_id):
        """Get a project by ID.

        :returns: project_ref
        :raises: keystone.exception.ProjectNotFound

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def update_project(self, project_id, project):
        """Updates an existing project.

        :raises: keystone.exception.ProjectNotFound,
                 keystone.exception.Conflict

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def delete_project(self, project_id):
        """Deletes an existing project.

        :raises: keystone.exception.ProjectNotFound

        """
        raise exception.NotImplemented()  # pragma: no cover

    # role crud

    @abc.abstractmethod
    def create_role(self, role_id, role):
        """Creates a new role.

        :raises: keystone.exception.Conflict

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_roles(self, hints):
        """List roles in the system.

        :param hints: filter hints which the driver should
                      implement if at all possible.

        :returns: a list of role_refs or an empty list.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def list_roles_from_ids(self, role_ids):
        """List roles for the provided list of ids.

        :param role_ids: list of ids

        :returns: a list of role_refs.

        This method is used internally by the assignment manager to bulk read
        a set of roles given their ids.

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def get_role(self, role_id):
        """Get a role by ID.

        :returns: role_ref
        :raises: keystone.exception.RoleNotFound

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def update_role(self, role_id, role):
        """Updates an existing role.

        :raises: keystone.exception.RoleNotFound,
                 keystone.exception.Conflict

        """
        raise exception.NotImplemented()  # pragma: no cover

    @abc.abstractmethod
    def delete_role(self, role_id):
        """Deletes an existing role.

        :raises: keystone.exception.RoleNotFound

        """
        raise exception.NotImplemented()  # pragma: no cover

    # Domain management functions for backends that only allow a single
    # domain.  Currently, this is only LDAP, but might be used by other
    # backends in the future.
    def _set_default_domain(self, ref):
        """If the domain ID has not been set, set it to the default."""
        if isinstance(ref, dict):
            if 'domain_id' not in ref:
                ref = ref.copy()
                ref['domain_id'] = CONF.identity.default_domain_id
            return ref
        elif isinstance(ref, list):
            return [self._set_default_domain(x) for x in ref]
        else:
            raise ValueError(_('Expected dict or list: %s') % type(ref))

    def _validate_default_domain(self, ref):
        """Validate that either the default domain or nothing is specified.

        Also removes the domain from the ref so that LDAP doesn't have to
        persist the attribute.

        """
        ref = ref.copy()
        domain_id = ref.pop('domain_id', CONF.identity.default_domain_id)
        self._validate_default_domain_id(domain_id)
        return ref

    def _validate_default_domain_id(self, domain_id):
        """Validate that the domain ID specified belongs to the default domain.

        """
        if domain_id != CONF.identity.default_domain_id:
            raise exception.DomainNotFound(domain_id=domain_id)
