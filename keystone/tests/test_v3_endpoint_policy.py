# Copyright 2014 IBM Corp.
#
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

from keystone.common import dependency
from keystone.contrib import endpoint_policy  # flake8: noqa
from keystone.tests import test_v3


@dependency.requires('endpoint_policy_api')
class TestExtensionCase(test_v3.RestfulTestCase):

    EXTENSION_NAME = 'endpoint_policy'
    EXTENSION_TO_ADD = 'endpoint_policy_extension'


class EndpointPolicyTestCase(TestExtensionCase):
    """Test endpoint policy CRUD."""

    def setUp(self):
        super(EndpointPolicyTestCase, self).setUp()
        self.policy = self.new_policy_ref()
        self.policy_api.create_policy(self.policy['id'], self.policy)
        self.service = self.new_service_ref()
        self.catalog_api.create_service(self.service['id'], self.service)
        self.endpoint = self.new_endpoint_ref(self.service['id'])
        self.catalog_api.create_endpoint(self.endpoint['id'], self.endpoint)

    # endpoint policy crud tests

    def test_crud_for_policy_for_explicit_endpoint(self):
        """PUT, HEAD and DELETE for explicit endpoint policy"""

        self.put('/OS-ENDPOINT-POLICY/policies/%(policy_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                     'policy_id': self.policy['id'],
                     'endpoint_id': self.endpoint['id']},
                 body='',
                 expected_status=204)

        self.head('/OS-ENDPOINT-POLICY/policies/%(policy_id)s'
                  '/endpoints/%(endpoint_id)s' % {
                      'policy_id': self.policy['id'],
                      'endpoint_id': self.endpoint['id']},
                  body='',
                  expected_status=204)

        self.delete('/OS-ENDPOINT-POLICY/policies/%(policy_id)s'
                    '/endpoints/%(endpoint_id)s' % {
                        'policy_id': self.policy['id'],
                        'endpoint_id': self.endpoint['id']},
                    body='',
                    expected_status=204)
