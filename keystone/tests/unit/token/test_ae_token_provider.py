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

import uuid

from keystone import exception
from keystone import tests
from keystone.token.providers import ae_tokens


class TestAeTokenProvider(tests.TestCase):
    def setUp(self):
        super(TestAeTokenProvider, self).setUp()
        self.provider = ae_tokens.Provider()

    def test_issue_v2_token_raises_not_implemented(self):
        """Test that exception is raised when call creating v2 token."""
        token_ref = {}
        self.assertRaises(exception.NotImplemented,
                          self.provider.issue_v2_token,
                          token_ref)

    def test_issue_v3_token_raises_not_implemented(self):
        """Test that exception is raised when call creating v3 token."""
        user_id = uuid.uuid4().hex
        method_names = {}
        self.assertRaises(exception.NotImplemented,
                          self.provider.issue_v3_token,
                          user_id,
                          method_names)

    def test_validate_v2_token_raises_not_implemented(self):
        """Test that exception is raised when validating a v2 token."""
        token_ref = {}
        self.assertRaises(exception.NotImplemented,
                          self.provider.validate_v2_token,
                          token_ref)

    def test_validate_v3_token_raises_not_implemented(self):
        """Test that exception is raised when validating a v3 token."""
        token_ref = {}
        self.assertRaises(exception.NotImplemented,
                          self.provider.validate_v3_token,
                          token_ref)

    def test_get_token_id_raises_not_implemented(self):
        """Test that an exception is raised when calling _get_token_id."""
        token_data = {}
        self.assertRaises(exception.NotImplemented,
                          self.provider._get_token_id, token_data)
