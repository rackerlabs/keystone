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

from keystone.common import context
from keystone.tests import unit


class TestRequestContext(unit.TestCase):
    
    def setUp(self):
        super().setUp()
        self.user_id = uuid.uuid4().hex
        self.project_id = uuid.uuid4().hex
        self.domain_id = uuid.uuid4().hex
        
    def test_to_policy_values_with_token_reference(self):
        """Test to_policy_values when token_reference exists."""
        request_context = context.RequestContext(
            user_id=self.user_id,
            project_id=self.project_id,
            domain_id=self.domain_id
        )
        
        # Set token_reference attribute
        token_data = {'token': 'test-token-value'}
        request_context.token_reference = token_data
        
        policy_values = request_context.to_policy_values()
        
        # Verify token is included in policy values
        self.assertEqual(policy_values['token'], 'test-token-value')
        self.assertEqual(policy_values['domain_id'], self.domain_id)
        
    def test_to_policy_values_without_token_reference(self):
        """Test to_policy_values when token_reference doesn't exist."""
        request_context = context.RequestContext(
            user_id=self.user_id,
            project_id=self.project_id,
            domain_id=self.domain_id
        )
        
        # Ensure token_reference doesn't exist
        self.assertFalse(hasattr(request_context, 'token_reference'))
        
        # This should not raise an exception
        policy_values = request_context.to_policy_values()
        
        # Verify token is not in policy values but other values are present
        self.assertNotIn('token', policy_values)
        self.assertEqual(policy_values['domain_id'], self.domain_id)
        
    def test_to_policy_values_with_none_domain_id(self):
        """Test to_policy_values when domain_id is None."""
        request_context = context.RequestContext(
            user_id=self.user_id,
            project_id=self.project_id
        )
        
        policy_values = request_context.to_policy_values()
        
        # Verify domain_id is None when not set
        self.assertIsNone(policy_values['domain_id']) 