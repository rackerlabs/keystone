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

from unittest import mock

from keystone.common import provider_api
from keystone.common import render_token
from keystone.models import token_model
from keystone.tests import unit


PROVIDERS = provider_api.ProviderAPIs


class TestRenderToken(unit.TestCase):
    def test_missing_password_expires_at(self):
        identity_mock = mock.MagicMock()
        PROVIDERS._register_provider_api("identity_api", identity_mock)
        user_id = 'user-id'
        identity_mock.get_user.return_value = {
            'id': user_id,
            'name': 'foobar',
            'domain_id': 'default',
            'enabled': True,
            'email': 'foobar@example.com',
        }

        resource_mock = mock.MagicMock()
        PROVIDERS._register_provider_api("resource_api", resource_mock)
        resource_mock.get_domain.return_value = {
            'id': 'default',
            'name': 'Default',
        }

        federation_mock = mock.MagicMock()
        PROVIDERS._register_provider_api("federation_api", federation_mock)
        federation_mock.get_enabled_service_providers.return_value = []

        token = token_model.TokenModel()
        token.user_id = user_id
        token.audit_id = 'audit-id'
        token.expires_at = '2026-01-01T00:00:00Z'

        result = render_token.render_token_response_from_model(token)

        self.assertIn('user', result['token'])
        self.assertIsNone(result['token']['user']['password_expires_at'])
