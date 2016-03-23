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

import functools
import os
import threading

from oslo_config import cfg
from oslo_log import log

from keystone.common import config
from keystone.common import dependency
from keystone.common import manager
from keystone import exception
from keystone.i18n import _, _LW


CONF = cfg.CONF

LOG = log.getLogger(__name__)

DOMAIN_CONF_FHEAD = 'keystone.'
DOMAIN_CONF_FTAIL = '.conf'

# The number of times we will attempt to register a domain to use the SQL
# driver, if we find that another process is in the middle of registering or
# releasing at the same time as us.
REGISTRATION_ATTEMPTS = 10

# Config Registration Types
SQL_DRIVER = 'SQL'


@dependency.requires('domain_config_api', 'resource_api')
class DomainConfigs(dict):
    """Discover, store and provide access to domain specific configs.

    The setup_domain_drivers() call will be made via the wrapper from
    the first call to any driver function handled by this manager.

    Domain specific configurations are only supported for the identity backend
    and the individual configurations are either specified in the resource
    database or in individual domain configuration files, depending on the
    setting of the 'domain_configurations_from_database' config option.

    The result will be that for each domain with a specific configuration,
    this class will hold a reference to a ConfigOpts and driver object that
    the identity manager and driver can use.

    """

    configured = False
    driver = None
    _any_sql = False
    lock = threading.Lock()
    identity_manager = None

    def __init__(self, identity_manager):
        self.identity_manager = identity_manager

    def _load_driver(self, domain_config):
        return manager.load_driver(self.identity_manager.driver_namespace,
                                   domain_config['cfg'].identity.driver,
                                   domain_config['cfg'])

    def _load_config_from_file(self, resource_api, file_list, domain_name):

        def _assert_no_more_than_one_sql_driver(domain_id, new_config,
                                                config_file):
            """Ensure there is no more than one sql driver.

            Check to see if the addition of the driver in this new config
            would cause there to be more than one sql driver.

            """
            if (new_config['driver'].is_sql and
                    (self.driver.is_sql or self._any_sql)):
                # The addition of this driver would cause us to have more than
                # one sql driver, so raise an exception.
                raise exception.MultipleSQLDriversInConfig(source=config_file)
            self._any_sql = self._any_sql or new_config['driver'].is_sql

        try:
            domain_ref = resource_api.get_domain_by_name(domain_name)
        except exception.DomainNotFound:
            LOG.warning(
                _LW('Invalid domain name (%s) found in config file name'),
                domain_name)
            return

        # Create a new entry in the domain config dict, which contains
        # a new instance of both the conf environment and driver using
        # options defined in this set of config files.  Later, when we
        # service calls via this Manager, we'll index via this domain
        # config dict to make sure we call the right driver
        domain_config = {}
        domain_config['cfg'] = cfg.ConfigOpts()
        config.configure(conf=domain_config['cfg'])
        domain_config['cfg'](args=[], project='keystone',
                             default_config_files=file_list)
        domain_config['driver'] = self._load_driver(domain_config)
        _assert_no_more_than_one_sql_driver(domain_ref['id'],
                                            domain_config,
                                            file_list)
        self[domain_ref['id']] = domain_config

    def _setup_domain_drivers_from_files(self, standard_driver, resource_api):
        """Read the domain specific configuration files and load the drivers.

        Domain configuration files are stored in the domain config directory,
        and must be named of the form:

        keystone.<domain_name>.conf

        For each file, call the load config method where the domain_name
        will be turned into a domain_id and then:

        - Create a new config structure, adding in the specific additional
          options defined in this config file
        - Initialise a new instance of the required driver with this new config

        """
        conf_dir = CONF.identity.domain_config_dir
        if not os.path.exists(conf_dir):
            LOG.warning(_LW('Unable to locate domain config directory: %s'),
                        conf_dir)
            return

        for r, d, f in os.walk(conf_dir):
            for fname in f:
                if (fname.startswith(DOMAIN_CONF_FHEAD) and
                        fname.endswith(DOMAIN_CONF_FTAIL)):
                    if fname.count('.') >= 2:
                        self._load_config_from_file(
                            resource_api, [os.path.join(r, fname)],
                            fname[len(DOMAIN_CONF_FHEAD):
                                  -len(DOMAIN_CONF_FTAIL)])
                    else:
                        LOG.debug(('Ignoring file (%s) while scanning domain '
                                   'config directory'),
                                  fname)

    def _load_config_from_database(self, domain_id, specific_config):

        def _assert_no_more_than_one_sql_driver(domain_id, new_config):
            """Ensure adding driver doesn't push us over the limit of 1

            The checks we make in this method need to take into account that
            we may be in a multiple process configuration and ensure that
            any race conditions are avoided.

            """
            if not new_config['driver'].is_sql:
                self.domain_config_api.release_registration(domain_id)
                return

            # To ensure the current domain is the only SQL driver, we attempt
            # to register our use of SQL. If we get it we know we are good,
            # if we fail to register it then we should:
            #
            # - First check if another process has registered for SQL for our
            #   domain, in which case we are fine
            # - If a different domain has it, we should check that this domain
            #   is still valid, in case, for example, domain deletion somehow
            #   failed to remove its registration (i.e. we self heal for these
            #   kinds of issues).

            domain_registered = 'Unknown'
            for attempt in range(REGISTRATION_ATTEMPTS):
                if self.domain_config_api.obtain_registration(
                        domain_id, SQL_DRIVER):
                    LOG.debug('Domain %s successfully registered to use the '
                              'SQL driver.', domain_id)
                    return

                # We failed to register our use, let's find out who is using it
                try:
                    domain_registered = (
                        self.domain_config_api.read_registration(
                            SQL_DRIVER))
                except exception.ConfigRegistrationNotFound:
                    msg = ('While attempting to register domain %(domain)s to '
                           'use the SQL driver, another process released it, '
                           'retrying (attempt %(attempt)s).')
                    LOG.debug(msg, {'domain': domain_id,
                                    'attempt': attempt + 1})
                    continue

                if domain_registered == domain_id:
                    # Another process already registered it for us, so we are
                    # fine. In the race condition when another process is
                    # in the middle of deleting this domain, we know the domain
                    # is already disabled and hence telling the caller that we
                    # are registered is benign.
                    LOG.debug('While attempting to register domain %s to use '
                              'the SQL driver, found that another process had '
                              'already registered this domain. This is normal '
                              'in multi-process configurations.', domain_id)
                    return

                # So we don't have it, but someone else does...let's check that
                # this domain is still valid
                try:
                    self.resource_api.get_domain(domain_registered)
                except exception.DomainNotFound:
                    msg = ('While attempting to register domain %(domain)s to '
                           'use the SQL driver, found that it was already '
                           'registered to a domain that no longer exists '
                           '(%(old_domain)s). Removing this stale '
                           'registration and retrying (attempt %(attempt)s).')
                    LOG.debug(msg, {'domain': domain_id,
                                    'old_domain': domain_registered,
                                    'attempt': attempt + 1})
                    self.domain_config_api.release_registration(
                        domain_registered, type=SQL_DRIVER)
                    continue

                # The domain is valid, so we really do have an attempt at more
                # than one SQL driver.
                details = (
                    _('Config API entity at /domains/%s/config') % domain_id)
                raise exception.MultipleSQLDriversInConfig(source=details)

            # We fell out of the loop without either registering our domain or
            # being able to find who has it...either we were very very very
            # unlucky or something is awry.
            msg = _('Exceeded attempts to register domain %(domain)s to use '
                    'the SQL driver, the last domain that appears to have '
                    'had it is %(last_domain)s, giving up') % {
                        'domain': domain_id, 'last_domain': domain_registered}
            raise exception.UnexpectedError(msg)

        domain_config = {}
        domain_config['cfg'] = cfg.ConfigOpts()
        config.configure(conf=domain_config['cfg'])
        domain_config['cfg'](args=[], project='keystone',
                             default_config_files=[])

        # Override any options that have been passed in as specified in the
        # database.
        for group in specific_config:
            for option in specific_config[group]:
                domain_config['cfg'].set_override(
                    option, specific_config[group][option],
                    group, enforce_type=True)

        domain_config['cfg_overrides'] = specific_config
        domain_config['driver'] = self._load_driver(domain_config)
        _assert_no_more_than_one_sql_driver(domain_id, domain_config)
        self[domain_id] = domain_config

    def _setup_domain_drivers_from_database(self, standard_driver,
                                            resource_api):
        """Read domain specific configuration from database and load drivers.

        Domain configurations are stored in the domain-config backend,
        so we go through each domain to find those that have a specific config
        defined, and for those that do we:

        - Create a new config structure, overriding any specific options
          defined in the resource backend
        - Initialise a new instance of the required driver with this new config

        """
        for domain in resource_api.list_domains():
            domain_config_options = (
                self.domain_config_api.
                get_config_with_sensitive_info(domain['id']))
            if domain_config_options:
                self._load_config_from_database(domain['id'],
                                                domain_config_options)

    def setup_domain_drivers(self, standard_driver, resource_api):
        # This is called by the api call wrapper
        self.driver = standard_driver

        if CONF.identity.domain_configurations_from_database:
            self._setup_domain_drivers_from_database(standard_driver,
                                                     resource_api)
        else:
            self._setup_domain_drivers_from_files(standard_driver,
                                                  resource_api)
        self.configured = True

    def get_domain_driver(self, domain_id):
        self.check_config_and_reload_domain_driver_if_required(domain_id)
        if domain_id in self:
            return self[domain_id]['driver']

    def get_domain_conf(self, domain_id):
        self.check_config_and_reload_domain_driver_if_required(domain_id)
        if domain_id in self:
            return self[domain_id]['cfg']
        else:
            return CONF

    def reload_domain_driver(self, domain_id):
        # Only used to support unit tests that want to set
        # new config values.  This should only be called once
        # the domains have been configured, since it relies on
        # the fact that the configuration files/database have already been
        # read.
        if self.configured:
            if domain_id in self:
                self[domain_id]['driver'] = (
                    self._load_driver(self[domain_id]))
            else:
                # The standard driver
                self.driver = self.driver()

    def check_config_and_reload_domain_driver_if_required(self, domain_id):
        """Check for, and load, any new domain specific config for this domain.

        This is only supported for the database-stored domain specific
        configuration.

        When the domain specific drivers were set up, we stored away the
        specific config for this domain that was available at that time. So we
        now read the current version and compare. While this might seem
        somewhat inefficient, the sensitive config call is cached, so should be
        light weight. More importantly, when the cache timeout is reached, we
        will get any config that has been updated from any other keystone
        process.

        This cache-timeout approach works for both multi-process and
        multi-threaded keystone configurations. In multi-threaded
        configurations, even though we might remove a driver object (that
        could be in use by another thread), this won't actually be thrown away
        until all references to it have been broken. When that other
        thread is released back and is restarted with another command to
        process, next time it accesses the driver it will pickup the new one.

        """
        if (not CONF.identity.domain_specific_drivers_enabled or
                not CONF.identity.domain_configurations_from_database):
            # If specific drivers are not enabled, then there is nothing to do.
            # If we are not storing the configurations in the database, then
            # we'll only re-read the domain specific config files on startup
            # of keystone.
            return

        latest_domain_config = (
            self.domain_config_api.
            get_config_with_sensitive_info(domain_id))
        domain_config_in_use = domain_id in self

        if latest_domain_config:
            if (not domain_config_in_use or
                    latest_domain_config != self[domain_id]['cfg_overrides']):
                self._load_config_from_database(domain_id,
                                                latest_domain_config)
        elif domain_config_in_use:
            # The domain specific config has been deleted, so should remove the
            # specific driver for this domain.
            try:
                del self[domain_id]
            except KeyError:  # nosec
                # Allow this error in case we are unlucky and in a
                # multi-threaded situation, two threads happen to be running
                # in lock step.
                pass
        # If we fall into the else condition, this means there is no domain
        # config set, and there is none in use either, so we have nothing
        # to do.


def domains_configured(f):
    """Wraps API calls to lazy load domain configs after init.

    This is required since the assignment manager needs to be initialized
    before this manager, and yet this manager's init wants to be
    able to make assignment calls (to build the domain configs).  So
    instead, we check if the domains have been initialized on entry
    to each call, and if requires load them,

    """
    @functools.wraps(f)
    def wrapper(self, *args, **kwargs):
        if (not self.domain_configs.configured and
                CONF.identity.domain_specific_drivers_enabled):
            # If domain specific driver has not been configured, acquire the
            # lock and proceed with loading the driver.
            with self.domain_configs.lock:
                # Check again just in case some other thread has already
                # completed domain config.
                if not self.domain_configs.configured:
                    self.domain_configs.setup_domain_drivers(
                        self.driver, self.resource_api)
        return f(self, *args, **kwargs)
    return wrapper


def exception_translated(exception_type):
    """Wraps API calls to map to correct exception."""
    def _exception_translated(f):
        @functools.wraps(f)
        def wrapper(self, *args, **kwargs):
            try:
                return f(self, *args, **kwargs)
            except exception.PublicIDNotFound as e:
                if exception_type == 'user':
                    raise exception.UserNotFound(user_id=str(e))
                elif exception_type == 'group':
                    raise exception.GroupNotFound(group_id=str(e))
                elif exception_type == 'assertion':
                    raise AssertionError(_('Invalid user / password'))
                else:
                    raise
        return wrapper
    return _exception_translated
