
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import abc
import logging

from oslo_config import cfg
import six

from keystone import backends
from keystone.common import dependency
from keystone.common import sql
from keystone import config
from keystone import service as keystone_service

CONF = cfg.CONF


@six.add_metaclass(abc.ABCMeta)
class AbstractApplication(object):
    """Common config initialization sequence

    `setup()` and `startup_application()` methods are to be overriden in
    subclasses::

        - `setup()` initializes everything needed ASAP;
        - `startup_application()` creates all to be created in order
          to start application
    """

    def __init__(self, version=None, config_files=None):
        # Configure
        config.configure()
        sql.initialize()
        config.set_default_for_default_log_levels()
        CONF(project='keystone', version=version,
             default_config_files=config_files)
        self.setup()
        config.setup_logging()

        self.app_conf_str = 'config:%s' % config.find_paste_config()

        # Log the options used when starting if we're in debug mode...
        if CONF.debug:
            CONF.log_opt_values(logging.getLogger(CONF.prog), logging.DEBUG)

        # Setup backends
        self.drivers = backends.load_backends()
        self.drivers.update(self.load_extra_backends())
        self.resource = self.startup_application()
        self.drivers.update(dependency.resolve_future_dependencies())

    @abc.abstractmethod
    def setup(self):
        raise NotImplemented()

    @abc.abstractmethod
    def startup_application(self):
        raise NotImplemented()

    def load_extra_backends(self):
        return {}

    def get_app(self, name):
        return keystone_service.loadapp(self.app_conf_str, name)


def configure(version=None, config_files=None,
              pre_setup_logging_fn=lambda: None):
    config.configure()
    sql.initialize()
    config.set_default_for_default_log_levels()

    CONF(project='keystone', version=version,
         default_config_files=config_files)

    pre_setup_logging_fn()
    config.setup_logging()


def setup_backends(load_extra_backends_fn=lambda: {},
                   startup_application_fn=lambda: None):
    drivers = backends.load_backends()
    drivers.update(load_extra_backends_fn())
    res = startup_application_fn()
    drivers.update(dependency.resolve_future_dependencies())
    return drivers, res
