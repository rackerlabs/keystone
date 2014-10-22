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

import base64
import uuid

from oslo.utils import timeutils

from keystone import exception
from keystone import tests
from keystone.token.providers import ae
from keystone.token.providers.ae import token_formatters


class TestAeTokenProvider(tests.TestCase):
    def setUp(self):
        super(TestAeTokenProvider, self).setUp()
        self.provider = ae.Provider()

    def test_issue_v2_token_raises_not_implemented(self):
        """Test that exception is raised when call creating v2 token."""
        token_ref = {}
        self.assertRaises(exception.NotImplemented,
                          self.provider.issue_v2_token,
                          token_ref)

    def test_validate_v2_token_raises_not_implemented(self):
        """Test that exception is raised when validating a v2 token."""
        token_ref = {}
        self.assertRaises(exception.NotImplemented,
                          self.provider.validate_v2_token,
                          token_ref)

    def test_get_token_id_raises_not_implemented(self):
        """Test that an exception is raised when calling _get_token_id."""
        token_data = {}
        self.assertRaises(exception.NotImplemented,
                          self.provider._get_token_id, token_data)


class TestBaseTokenFormatter(tests.TestCase):
    def setUp(self):
        super(TestBaseTokenFormatter, self).setUp()
        self.formatter = token_formatters.BaseTokenFormatter()

    def test_uuid_hex_to_byte_conversions(self):
        expected_hex_uuid = uuid.uuid4().hex
        uuid_obj = uuid.UUID('{' + expected_uuid_in_bytes+ '}')
        expected_uuid_in_bytes = uuid_obj.bytes
        actual_uuid_in_bytes = self.formatter._convert_uuid_hex_to_bytes(
                hex_uuid)
        self.assertEqual(expected_uuid_in_bytes, actual_uuid_in_bytes)
        actual_hex_uuid = self.formatter._convert_uuid_bytes_to_hex(
                expected_uuid_in_bytes)
        self.assertEqual(expected_hex_uuid, actual_hex_uuid)

    def test_time_string_to_int_conversions(self):
        expected_time_str = timeutils.isotime(timeutils.utcnow())
        time_obj = timeutils.parse_isotime(expected_time_str)
        expected_time_int = int(time_obj.strftime('%s'))

        actual_time_int = self.formatter._convert_time_string_to_int(
                expected_time_str)
        self.assertEqual(expected_time_int, actual_time_int)

        actual_time_str = self.formatter._convert_int_to_time_string(
                actual_time_int)
        self.assertEqual(expected_time_str, actual_time_str)


class TestStandardTokenFormatter(tests.TestCase):
    def setUp(self):
        super(TestStandardTokenFormatter, self).setUp()
        self.formatter = token_formatters.StandardTokenFormatter()

    def test_token_encryption(self):
        exp_user_id = uuid.uuid4().hex
        exp_project_id = uuid.uuid4().hex
        exp_token_data = {'token': {}}
        some_time_string = timeutils.isotime(timeutils.utcnow())
        # All we are validating here is that the token is encrypted and
        # decrypted properly, not the actual validity of token data.
        exp_token_data['token']['issued_at'] = some_time_string
        exp_token_data['token']['expires_at'] = some_time_string
        audit_ids = base64.urlsafe_b64encode(uuid.uuid4().bytes)[:-2]
        exp_token_data['token']['audit_ids'] = audit_ids

        encrypted_token = self.formatter.create_token(exp_user_id,
                exp_project_id, exp_token_data)

        self.assertLess(len(encrypted_token), 255)

        user_id, project_id, token_data = self.formatter.validate_token(
                encrypted_token)

        self.assertEqual(exp_user_id, user_id)
        self.assertEqual(exp_project_id, project_id)
        exp_issued_at = exp_token_data['token']['issued_at']
        exp_expires_at = exp_token_data['token']['expires_at']
        exp_audit_ids = exp_token_data['token']['audit_ids']
        self.assertEqual(exp_issued_at, token_data['token']['issued_at'])
        self.assertEqual(exp_expires_at, token_data['token']['expires_at'])
        self.assertEqual(exp_audit_ids, token_data['token']['audit_ids'])
