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

import os

import fixtures

from keystone.common import file_utils
from keystone.common import jwt_utils


class JWTKeyRepository(fixtures.Fixture):
    def __init__(self, config_fixture):
        super(JWTKeyRepository, self).__init__()
        self.config_fixture = config_fixture
        self.key_group = 'jwt_tokens'

    def setUp(self):
        super(JWTKeyRepository, self).setUp()
        directory = self.useFixture(fixtures.TempDir()).path
        self.config_fixture.config(group=self.key_group,
                                   key_repository=directory)

        file_utils.create_directory(directory)
        private_key_path = os.path.join(directory, 'private.pem')
        public_key_path = os.path.join(directory, 'public.pem')
        jwt_utils.create_key_pair(private_key_path, public_key_path)
