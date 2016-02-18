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
import uuid

from rally.task import atomic
from rally.task import scenario


class KeystoneRoleAPIRallyTest(scenario.Scenario):

    @staticmethod
    def _new_role_ref():
        ref = {
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex,
            'domain_id': None
        }
        return ref

    @atomic.action_timer("create_and_delete_implied_roles")
    def create_and_delete_implied_roles(self):
        ks_adm_client = self.admin_clients("keystone")
        admin_token = ks_adm_client.auth_token
        public_url = ks_adm_client.auth_url

        role_ref = self.new_role_ref()
        requests.post(public_url + '/v3/roles',
                      headers={'X-Auth-Token': admin_token},
                      body={'role': role_ref})

        implied_role_ref = self.new_role_ref()
        requests.post(public_url + '/v3/roles',
                      headers={'X-Auth-Token': admin_token},
                      body={'role': implied_role_ref})
        requests.put('%s/v3/roles/%s/implies/%s' % (
                     public_url,
                     role_ref['id'], implied_role_ref['id']),
                     headers={'X-Auth-Token': admin_token})

        resp = requests.get(public_url + '/v3/roles/' + implied_role_ref['id'],
                            headers={'X-Auth-Token': admin_token})

        assert(resp.status_code == 200)

        requests.delete('%s/v3/roles/%s/implies/%s' % (
                        public_url,
                        role_ref['id'], implied_role_ref['id']),
                        headers={'X-Auth-Token': admin_token})

        resp = requests.get(public_url + '/v3/roles/' + implied_role_ref['id'],
                            headers={'X-Auth-Token': admin_token})

        assert(resp.status_code == 404)
