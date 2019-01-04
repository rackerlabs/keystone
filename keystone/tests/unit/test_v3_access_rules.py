# Copyright 2019 SUSE Linux GmbH
#
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

from six.moves import http_client

from keystone.tests.unit import test_v3


class AccessRuleTestCase(test_v3.RestfulTestCase):
    """Test list operation for access rules."""

    def test_list_access_rules(self):
        with self.test_client() as c:
            token = self.get_scoped_token()
            resp = c.get('/v3/access_rules',
                         expected_status_code=http_client.OK,
                         headers={'X-Auth-Token': token})
            # TODO(cmurphy) not this
            self.assertEqual(1, len(resp.json))
