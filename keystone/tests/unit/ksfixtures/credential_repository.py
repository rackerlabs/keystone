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

import fixtures

from keystone.common import fernet_utils as utils
import keystone.conf

CONF = keystone.conf.CONF


# FIXME(lbragstad): We already have a KeyRepository fixture. We should make it
# so that you can just pass key repository information into it so that we can
# use it for testing the fernet token provider and the fernet credential
# provider.
class CredentialRepository(fixtures.Fixture):
    def __init__(self, config_fixture):
        super(CredentialRepository, self).__init__()
        self.config_fixture = config_fixture

    def setUp(self):
        super(CredentialRepository, self).setUp()
        directory = self.useFixture(fixtures.TempDir()).path
        self.config_fixture.config(group='credential',
                                   key_repository=directory)

        fernet_utils = utils.FernetUtils(
            CONF.credential.key_repository,
            CONF.credential.max_active_keys
        )
        fernet_utils.create_key_directory()
        fernet_utils.initialize_key_repository()
