
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


from keystone import backends
from keystone.common import dependency
from keystone.common import sql
from keystone import config


CONF = config.CONF


class ConfigWrapper(object):

    _configured = False

    def __init__(self, version=None, config_files=None):
        self.version = version
        self.config_files = config_files

    def __enter__(self):
        if not self.__class__._configured:
            config.configure()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.__class__._configured:
            config.setup_logging()
            sql.initialize()
            config.set_default_for_default_log_levels()

            CONF(project='keystone', version=self.version,
                 default_config_files=self.config_files)
            self.__class__._configured = True

            config.setup_logging()


def configure(version=None, config_files=None):
    with ConfigWrapper(version, config_files):
        pass


def setup_backends(load_extra_backends_fn=lambda: {},
                   startup_application_fn=lambda: None):
    drivers = backends.load_backends()
    drivers.update(load_extra_backends_fn())
    res = startup_application_fn()
    drivers.update(dependency.resolve_future_dependencies())
    return drivers, res
