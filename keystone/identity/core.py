# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

"""Main entry point into the Identity service."""

import copy
import os

from oslo.config import cfg

from keystone import assignment
from keystone import clean
from keystone import config
from keystone.common import dependency
from keystone import exception
from keystone.openstack.common import importutils
from keystone.common import logging
from keystone.common import manager



CONF = config.CONF

LOG = logging.getLogger(__name__)


def filter_user(user_ref):
    """Filter out private items in a user dict.

    'password', 'tenants' and 'groups' are never returned.

    :returns: user_ref

    """
    if user_ref:
        user_ref = user_ref.copy()
        user_ref.pop('password', None)
        user_ref.pop('tenants', None)
        user_ref.pop('groups', None)
        user_ref.pop('domains', None)
        try:
            user_ref['extra'].pop('password', None)
            user_ref['extra'].pop('tenants', None)
        except KeyError:
            pass
    return user_ref


@dependency.provider('identity_api')
class Manager(manager.Manager):
    """Default pivot point for the Identity backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    The identity manager handles the support of domain specific backends. Provided
    this feature is enabled, on init the Manager will scan the domain config dir
    for files of the form

    keystone.<domain_name>.conf

    For each of these, the domain_name will be turned into a domain_id and then
    the Manager will:
    - Create a new config structure, adding in the specific additional options
      defined in this config file
    - Initialise a new instance of the required driver with this new config

    Each of the identity calls are then pre-processed here to chose, based on
    domain, which of the drivers should be called. The non-domain-specific
    driver is still in place, and is used if there is no specific driver for
    the domain in question.

    """

    def __init__(self, assignment_api=None):
        super(Manager, self).__init__(CONF.identity.driver)
        if assignment_api is None:
            assignment_api = assignment.Manager(self)
        self.assignment_api = assignment_api
        self.driver.assignment_api = assignment_api
        self.domain_configs = {}
        if CONF.identity.domain_specific_drivers_enabled:
            self._setup_domain_configs()

    def _load_domain_config(self, file_list, domain_name):
        try:
            domain_ref = self.assignment_api.get_domain_by_name(domain_name)
        except:
            msg = _('Invalid domain name (%s) found in config file name') % domain_name
            LOG.warning(msg)
        else:
            domain = domain_ref['id']
            self.domain_configs[domain] = {}
            self.domain_configs[domain]['cfg'] = cfg.ConfigOpts()
            config.configure(conf=self.domain_configs[domain]['cfg'])
            self.domain_configs[domain]['cfg'](args=[], project='keystone',
                                               default_config_files=file_list)
            self.domain_configs[domain]['driver'] = (
                importutils.import_object(
                    self.domain_configs[domain]['cfg'].identity.driver))

    def _setup_domain_configs(self):
        if CONF.identity.domain_config_dir:
            if os.path.exists(CONF.identity.domain_config_dir):
                conf_dir = CONF.identity.domain_config_dir
            else:
                raise RuntimeError(_('Unable to locate domain config '
                                     'dir: %s') % CONF.identity.domain_config_dir)
        else:
            # TODO(henry-nash) find the dir of the keystone.conf file and look there
            raise RuntimeError(_('No domain config dir defined'))

        for r,d,f in os.walk(conf_dir):
            for file in f:
                if file.endswith(".conf"):
                     names = file.split('.')
                     if len(names) == 3:
                         self._load_domain_config([os.path.join(r,file)], names[1])

    def _select_driver(self, domain_id):
        if domain_id in self.domain_configs:
            driver = self.domain_configs[domain_id]['driver']
        else:
            driver = self.driver
        return driver 

    def _set_domain_id(self, ref, domain_id):
        if isinstance(ref, dict):
            ref = ref.copy()
            ref['domain_id'] = domain_id
            return ref
        elif isinstance(ref, list):
            return [self._set_domain_id(x, domain_id) for x in ref]
        else:
            raise ValueError(_('Expected dict or list: %s') % type(ref))

    def _clear_domain_id(self, ref):
        # Clear the domain_id, and then check to ensure that if this
        # was not the default domain, it is being handled by its own
        # backend driver.
        domain_id = ref.pop('domain_id', CONF.identity.default_domain_id)
        if (domain_id != CONF.identity.default_domain_id and
            domain_id not in self.domain_configs):
            raise exception.DomainNotFound(domain_id=domain_id)
        return ref

    def _normalize_scope(self, domain_scope):
        if domain_scope is None:
            domain_scope = CONF.identity.default_domain_id
        return domain_scope

    # All driver calls are pre-processed here in the Manager layer

    def authenticate(self, user_id, password, domain_scope=None):
        domain_id = self._normalize_scope(domain_scope)
        driver = self._select_driver(domain_id)
        ref = driver.authenticate(user_id, password)
        if not driver.is_domain_aware():
            ref = self._set_domain_id(ref, domain_id)
        return ref

    def create_user(self, user_id, user_ref):
        user = user_ref.copy()
        user['name'] = clean.user_name(user['name'])
        user.setdefault('enabled', True)
        user['enabled'] = clean.user_enabled(user['enabled'])

        # For creating a user,the domain is in the object itself
        domain_id = user_ref['domain_id']
        driver = self._select_driver(domain_id)
        if not driver.is_domain_aware():
            user = self._clear_domain_id(user)
        ref = self.driver.create_user(user_id, user)
        if not driver.is_domain_aware():
            ref = self._set_domain_id(ref, domain_id)
        return ref

    def get_user(self, user_id, domain_scope=None):
        domain_id = self._normalize_scope(domain_scope)
        driver = self._select_driver(domain_id)
        ref = driver.get_user(user_id)
        if not driver.is_domain_aware():
            ref = self._set_domain_id(ref, domain_id)
        return ref

    def get_user_by_name(self, user_name, domain_id):
        driver = self._select_driver(domain_id)
        ref = driver.get_user_by_name(user_name, domain_id)
        if not driver.is_domain_aware():
            ref = self._set_domain_id(ref, domain_id)
        return ref

    def list_users(self, domain_scope=None):
        domain_id = self._normalize_scope(domain_scope)
        driver = self._select_driver(domain_id)
        user_list = driver.list_users()
        if not driver.is_domain_aware():
            user_list = self._set_domain_id(user_list, domain_id)
        return user_list
        
    def update_user(self, user_id, user_ref, domain_scope=None):
        user = user_ref.copy()
        if 'name' in user:
            user['name'] = clean.user_name(user['name'])
        if 'enabled' in user:
            user['enabled'] = clean.user_enabled(user['enabled'])

        domain_id = self._normalize_scope(domain_scope)
        driver = self._select_driver(domain_id)
        if not driver.is_domain_aware():
            user = self._clear_domain_id(user)
        ref = self.driver.update_user(user_id, user)
        if not driver.is_domain_aware():
            ref = self._set_domain_id(ref, domain_id)
        return ref

    def delete_user(self, user_id, domain_scope=None):
        domain_id = self._normalize_scope(domain_scope)
        self._select_driver(domain_id).delete_user(user_id)

    # TODO(henry-nash) To the same as the above for all the other identity
    # calls.

    def create_group(self, group_id, group_ref):
        group = group_ref.copy()
        group.setdefault('description', '')
        return self.driver.create_group(group_id, group)

    # TODO(henry-nash, ayoung) The following cross calls to the assignment
    # API should be removed with the controller and tests making the correct
    # calls direct to assignment.
    
    def create_project(self, tenant_id, tenant_ref):
        tenant = tenant_ref.copy()
        tenant.setdefault('enabled', True)
        tenant['enabled'] = clean.project_enabled(tenant['enabled'])
        tenant.setdefault('description', '')
        return self.assignment_api.create_project(tenant_id, tenant)

    def update_project(self, tenant_id, tenant_ref):
        tenant = tenant_ref.copy()
        if 'enabled' in tenant:
            tenant['enabled'] = clean.project_enabled(tenant['enabled'])
        return self.assignment_api.update_project(tenant_id, tenant)

    def get_project_by_name(self, tenant_name, domain_id):
        return self.assignment_api.get_project_by_name(tenant_name, domain_id)

    def get_project(self, tenant_id):
        return self.assignment_api.get_project(tenant_id)

    def list_projects(self, domain_id=None):
        return self.assignment_api.list_projects(domain_id)

    def get_role(self, role_id):
        return self.assignment_api.get_role(role_id)

    def list_roles(self):
        return self.assignment_api.list_roles()

    def get_projects_for_user(self, user_id):
        return self.assignment_api.get_projects_for_user(user_id)

    def get_project_users(self, tenant_id):
        return self.assignment_api.get_project_users(tenant_id)

    def get_roles_for_user_and_project(self, user_id, tenant_id):
        return self.assignment_api.get_roles_for_user_and_project(
            user_id, tenant_id)

    def get_roles_for_user_and_domain(self, user_id, domain_id):
        return (self.assignment_api.get_roles_for_user_and_domain
                (user_id, domain_id))

    def _subrole_id_to_dn(self, role_id, tenant_id):
        return self.assignment_api._subrole_id_to_dn(role_id, tenant_id)

    def add_role_to_user_and_project(self, user_id,
                                     tenant_id, role_id):
        return (self.assignment_api.add_role_to_user_and_project
                (user_id, tenant_id, role_id))

    def create_role(self, role_id, role):
        return self.assignment_api.create_role(role_id, role)

    def delete_role(self, role_id):
        return self.assignment_api.delete_role(role_id)

    def delete_project(self, tenant_id):
        return self.assignment_api.delete_project(tenant_id)

    def remove_role_from_user_and_project(self, user_id,
                                          tenant_id, role_id):
        return (self.assignment_api.remove_role_from_user_and_project
                (user_id, tenant_id, role_id))

    def update_role(self, role_id, role):
        return self.assignment_api.update_role(role_id, role)

    def create_grant(self, role_id, user_id=None, group_id=None,
                     domain_id=None, project_id=None,
                     inherited_to_projects=False):
        return (self.assignment_api.create_grant
                (role_id, user_id, group_id, domain_id, project_id,
                 inherited_to_projects))

    def list_grants(self, user_id=None, group_id=None,
                    domain_id=None, project_id=None,
                    inherited_to_projects=False):
        return (self.assignment_api.list_grants
                (user_id, group_id, domain_id, project_id,
                 inherited_to_projects))

    def get_grant(self, role_id, user_id=None, group_id=None,
                  domain_id=None, project_id=None,
                  inherited_to_projects=False):
        return (self.assignment_api.get_grant
                (role_id, user_id, group_id, domain_id, project_id,
                 inherited_to_projects))

    def delete_grant(self, role_id, user_id=None, group_id=None,
                     domain_id=None, project_id=None,
                     inherited_to_projects=False):
        return (self.assignment_api.delete_grant
                (role_id, user_id, group_id, domain_id, project_id,
                 inherited_to_projects))

    def create_domain(self, domain_id, domain):
        return self.assignment_api.create_domain(domain_id, domain)

    def get_domain_by_name(self, domain_name):
        return self.assignment_api.get_domain_by_name(domain_name)

    def get_domain(self, domain_id):
        return self.assignment_api.get_domain(domain_id)

    def update_domain(self, domain_id, domain):
        return self.assignment_api.update_domain(domain_id, domain)

    def delete_domain(self, domain_id):
        return self.assignment_api.delete_domain(domain_id)

    def list_domains(self):
        return self.assignment_api.list_domains()

    def list_user_projects(self, user_id):
        return self.assignment_api.list_user_projects(user_id)

    def add_user_to_project(self, tenant_id, user_id):
        return self.assignment_api.add_user_to_project(tenant_id, user_id)

    def remove_user_from_project(self, tenant_id, user_id):
        return self.assignment_api.remove_user_from_project(tenant_id, user_id)

    def list_role_assignments(self):
        return self.assignment_api.list_role_assignments()  


class Driver(object):
    """Interface description for an Identity driver."""
    def authenticate(self, user_id, password):
        """Authenticate a given user and password.
        :returns: user_ref
        :raises: AssertionError
        """
        raise exception.NotImplemented()

    # user crud

    def create_user(self, user_id, user):
        """Creates a new user.

        :raises: keystone.exception.Conflict

        """
        raise exception.NotImplemented()

    def list_users(self):
        """List all users in the system.

        :returns: a list of user_refs or an empty list.

        """
        raise exception.NotImplemented()

    def list_users_in_group(self, group_id):
        """List all users in a group.

        :returns: a list of user_refs or an empty list.

        """
        raise exception.NotImplemented()

    def get_user(self, user_id):
        """Get a user by ID.

        :returns: user_ref
        :raises: keystone.exception.UserNotFound

        """
        raise exception.NotImplemented()

    def update_user(self, user_id, user):
        """Updates an existing user.

        :raises: keystone.exception.UserNotFound,
                 keystone.exception.Conflict

        """
        raise exception.NotImplemented()

    def add_user_to_group(self, user_id, group_id):
        """Adds a user to a group.

        :raises: keystone.exception.UserNotFound,
                 keystone.exception.GroupNotFound

        """
        raise exception.NotImplemented()

    def check_user_in_group(self, user_id, group_id):
        """Checks if a user is a member of a group.

        :raises: keystone.exception.UserNotFound,
                 keystone.exception.GroupNotFound

        """
        raise exception.NotImplemented()

    def remove_user_from_group(self, user_id, group_id):
        """Removes a user from a group.

        :raises: keystone.exception.NotFound

        """
        raise exception.NotImplemented()

    def delete_user(self, user_id):
        """Deletes an existing user.

        :raises: keystone.exception.UserNotFound

        """
        raise exception.NotImplemented()

    def get_user_by_name(self, user_name, domain_id):
        """Get a user by name.

        :returns: user_ref
        :raises: keystone.exception.UserNotFound

        """
        raise exception.NotImplemented()

    # group crud

    def create_group(self, group_id, group):
        """Creates a new group.

        :raises: keystone.exception.Conflict

        """
        raise exception.NotImplemented()

    def list_groups(self):
        """List all groups in the system.

        :returns: a list of group_refs or an empty list.

        """
        raise exception.NotImplemented()

    def list_groups_for_user(self, user_id):
        """List all groups a user is in

        :returns: a list of group_refs or an empty list.

        """
        raise exception.NotImplemented()

    def get_group(self, group_id):
        """Get a group by ID.

        :returns: group_ref
        :raises: keystone.exception.GroupNotFound

        """
        raise exception.NotImplemented()

    def update_group(self, group_id, group):
        """Updates an existing group.

        :raises: keystone.exceptionGroupNotFound,
                 keystone.exception.Conflict

        """
        raise exception.NotImplemented()

    def delete_group(self, group_id):
        """Deletes an existing group.

        :raises: keystone.exception.GroupNotFound

        """
        raise exception.NotImplemented()

    #end of identity

    # Assignments
