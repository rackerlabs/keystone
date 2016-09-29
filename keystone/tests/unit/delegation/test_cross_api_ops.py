# Licensed under the Apache License, Version 2.0 (the "License"); you may
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

from keystone.tests import unit
from keystone.tests.unit import test_v3_oauth1


__doc__ = """
Test scenarios:
- create trust,
  issue oauth1-scoped token,
  list access tokes,
  issue regular token
- create oauth1 request token,
  access token,
  issue trust-scoped token,
  issue regular token
- create assignment,
  list access tokens,
  issue oauth1-scoped token,
  issue trust-scoped token
"""


class DelegationCrossAPITest(test_v3_oauth1.OAuthFlowTests):

    def setUp(self):
        super(DelegationCrossAPITest, self).setUp()

        new_user = unit.new_user_ref(domain_id=self.domain_id)
        self.trustor_ref = self.identity_api.create_user(new_user)
        self.trustor_ref['password'] = new_user['password']

        new_user = unit.new_user_ref(domain_id=self.domain_id)
        self.trustee_ref = self.identity_api.create_user(new_user)
        self.trustee_ref['password'] = new_user['password']

        new_user = unit.new_user_ref(domain_id=self.domain_id)
        self.agent_ref = self.identity_api.create_user(new_user)
        self.agent_ref['password'] = new_user['password']

        self.roles = []
        for _ in range(3):
            new_role = unit.new_role_ref()
            self.roles.append(
                self.role_api.create_role(new_role['id'], new_role))

    def config_overrides(self):
        super(DelegationCrossAPITest, self).config_overrides()
        self.config_fixture.config(
            group='assignment',
            driver='keystone.delegation.backends.sql.AssignmentDriver')
        self.config_fixture.config(
            group='trust',
            driver='keystone.delegation.backends.sql.TrustDriver')
        self.config_fixture.config(
            group='oauth1',
            driver='keystone.delegation.backends.sql.OAuth1Driver')

    def _issue_regular_token(self, expected_status):
        # Assignment
        auth_data = self.build_authentication_request(
            user_id=self.trustee_ref['id'],
            password=self.trustee_ref['password'],
            project_id=self.project_id,)
        return self.v3_create_token(auth_data,
                                    expected_status=expected_status)

    def _issue_trust_scoped_token(self, delegation_id, expected_status):
        # Trust
        auth_data = self.build_authentication_request(
            user_id=self.trustee_ref['id'],
            password=self.trustee_ref['password'],
            trust_id=delegation_id)
        return self.v3_create_token(auth_data,
                                    expected_status=expected_status)

    def _list_access_tokens(self):
        # self.test_oauth_flow()
        # List access_tokens should be > 0
        resp = self.get('/users/%(user_id)s/OS-OAUTH1/access_tokens'
                        % {'user_id': self.trustee_ref['id']})
        entities = resp.result['access_tokens']
        self.assertTrue(entities)
        self.assertValidListLinks(resp.result['links'])

        return entities

    def _issue_oauth1_scoped_token(self, access_token_id, expected_status):
        pass


class DelegationAssignmentTest(DelegationCrossAPITest):

    def test_assignment_create(self):
        for role in self.roles:
            self.assignment_api.add_role_to_user_and_project(
                self.trustee_ref['id'], self.project_id, role['id'])
        delegations = self._list_access_tokens()
        delegation_id = delegations[0]['id']
        self._issue_regular_token(201)
        self._issue_trust_scoped_token(delegation_id, 200)
        self._issue_oauth1_scoped_token(delegation_id, 200)


class DelegationTrustTest(DelegationCrossAPITest):

    def setUp(self):
        super(DelegationTrustTest, self).setUp()
        trust_ref = unit.new_trust_ref(
            trustor_user_id=self.trustor_ref['id'],
            trustee_user_id=self.trustee_ref['id'],
            project_id=self.project_id,
            role_ids=[r['id'] for r in self.roles])

        # Create a trust between self.user and the first user in the list
        r = self.post('/OS-TRUST/trusts',
                      body={'trust': trust_ref})

        trust = self.assertValidTrustResponse(r)
        self.delegation = trust


class DelegationOAuth1Test(DelegationCrossAPITest):

    def setUp(self):
        super(DelegationOAuth1Test, self).setUp()
        self.test_oauth_flow()

    def test_assignment_delete(self):
        self._auth_all(False)

    def test_role_subset_revoke(self):
        self._auth_all(False)

    def test_trust_create(self):
        self._auth_all()

    def test_trust_delete(self):
        self._auth_all(False)

    def test_access_token_create(self):
        self._auth_all()

    def test_access_token_delete(self):
        self._auth_all(False)
