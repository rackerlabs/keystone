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

import requests
import testtools.matchers

from keystone.tests.functional import core as functests
from keystone.tests import unit


is_ok = testtools.matchers.Equals(requests.status_codes.codes.ok)


class TestRolesAPI(functests.BaseTestCase):

    def test_delete_role_also_deletes_implied_role(self):
        admin_token = self.get_scoped_admin_token()
        role_ref = unit.new_role_ref()
        requests.post(self.PUBLIC_URL + '/v3/roles',
                      headers={'X-Auth-Token': admin_token},
                      body={'role': role_ref})
        implied_role_ref = unit.new_role_ref()
        requests.post(self.PUBLIC_URL + '/v3/roles',
                      headers={'X-Auth-Token': admin_token},
                      body={'role': implied_role_ref})
        requests.put('%s/v3/roles/%s/implies/%s' % (
                     self.PUBLIC_URL,
                     role_ref['id'], implied_role_ref['id']),
                     headers={'X-Auth-Token': admin_token})
        resp = requests.delete('%s/v3/roles/%s/implies/%s' % (
                               self.PUBLIC_URL,
                               role_ref['id'], implied_role_ref['id']),
                               headers={'X-Auth-Token': admin_token})
        self.assertThat(resp.status_code, is_ok)
