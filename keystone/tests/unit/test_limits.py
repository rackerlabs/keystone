# Copyright 2013 OpenStack Foundation
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

from six.moves import http_client

from keystone.tests import unit
from keystone.tests.unit import test_v3


class RegisteredLimitsTestCase(test_v3.RestfulTestCase):
    """Test registered_limits & limits CRUD."""

    def test_create_registered_limit(self):
        """Call ``POST /registered_limits``"""
        ref = unit.new_registered_limit_ref()
        r = self.post(
            '/registered_limits',
            body={'registered_limits': [ref]},
            expected_status=http_client.CREATED)
        self.assertValidRegionResponse(r, ref)
