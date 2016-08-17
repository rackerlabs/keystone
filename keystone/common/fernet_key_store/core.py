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

from oslo_config import cfg
from oslo_log import log

from keystone.common import dependency
from keystone.common import manager


CONF = cfg.CONF
LOG = log.getLogger(__name__)


@dependency.provider('fernet_key_store_api')
class Manager(manager.Manager):

    driver_namespace = 'keystone.fernet_key_store'

    def __init__(self):
        super(Manager, self).__init__(CONF.fernet_tokens.key_store_driver)

    def initialize_key_repository(self, key_repository,
                                  max_active_keys,
                                  keystone_user_id=None,
                                  keystone_group_id=None):
        self.driver.initialize_key_repository(key_repository,
                                              max_active_keys,
                                              keystone_user_id,
                                              keystone_group_id)

    def rotate_keys(self, key_repository,
                    max_active_keys,
                    keystone_user_id=None,
                    keystone_group_id=None):
        self.driver.rotate_keys(key_repository,
                                max_active_keys,
                                keystone_user_id=None,
                                keystone_group_id=None)

    def validate_key_repository(self, key_repository,
                                requires_write=False):
        return self.driver.validate_key_repository(key_repository,
                                                   requires_write)

    def load_keys(self, key_repository, max_active_keys):
        return self.driver.load_keys(key_repository, max_active_keys)

    def create_key_directory(self, key_repository,
                             keystone_user_id=None,
                             keystone_group_id=None):
        return self.driver.create_key_directory(key_repository,
                                                keystone_user_id,
                                                keystone_group_id)
