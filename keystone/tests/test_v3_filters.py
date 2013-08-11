# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
# Copyright 2013 IBM Corp.
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

import tempfile
import uuid

from keystone import config
from keystone.openstack.common import jsonutils
from keystone.policy.backends import rules

import test_v3


CONF = config.CONF
DEFAULT_DOMAIN_ID = CONF.identity.default_domain_id


class IdentityTestFilteredCase(test_v3.RestfulTestCase):
    """Test policy enforcement on the v3 Identity API."""

    def setUp(self):
        """Setup for Identity Filter Test Cases.

        As well as the usual housekeeping, create a set of domains,
        users, roles and projects for the subsequent tests:

        - Three domains: A,B & C.  C is disabled.
        - DomainA has user1, DomainB has user2 and user3
        - DomainA has group1 and group2, DomainB has group3
        - User1 has a role on DomainA

        Remember that there will also be a fourth domain in existence,
        the default domain.

        """
        # Ensure that test_v3.RestfulTestCase doesn't load its own
        # sample data, which would make checking the results of our
        # tests harder
        super(IdentityTestFilteredCase, self).setUp(load_sample_data=False)
        # Start by creating a couple of domains
        self.domainA = self.new_domain_ref()
        self.identity_api.create_domain(self.domainA['id'], self.domainA)
        self.domainB = self.new_domain_ref()
        self.identity_api.create_domain(self.domainB['id'], self.domainB)
        self.domainC = self.new_domain_ref()
        self.domainC['enabled'] = False
        self.identity_api.create_domain(self.domainC['id'], self.domainC)

        # Now create some users, one in domainA and two of them in domainB
        self.user1 = self.new_user_ref(domain_id=self.domainA['id'])
        self.user1['password'] = uuid.uuid4().hex
        self.identity_api.create_user(self.user1['id'], self.user1)

        self.user2 = self.new_user_ref(domain_id=self.domainB['id'])
        self.user2['password'] = uuid.uuid4().hex
        self.identity_api.create_user(self.user2['id'], self.user2)

        self.user3 = self.new_user_ref(domain_id=self.domainB['id'])
        self.user3['password'] = uuid.uuid4().hex
        self.identity_api.create_user(self.user3['id'], self.user3)

        self.group1 = self.new_group_ref(domain_id=self.domainA['id'])
        self.identity_api.create_group(self.group1['id'], self.group1)

        self.group2 = self.new_group_ref(domain_id=self.domainA['id'])
        self.identity_api.create_group(self.group2['id'], self.group2)

        self.group3 = self.new_group_ref(domain_id=self.domainB['id'])
        self.identity_api.create_group(self.group3['id'], self.group3)

        self.role = self.new_role_ref()
        self.identity_api.create_role(self.role['id'], self.role)
        self.identity_api.create_grant(self.role['id'],
                                       user_id=self.user1['id'],
                                       domain_id=self.domainA['id'])

        # Initialize the policy engine and allow us to write to a temp
        # file in each test to create the policies
        self.orig_policy_file = CONF.policy_file
        rules.reset()
        _unused, self.tmpfilename = tempfile.mkstemp()
        self.opt(policy_file=self.tmpfilename)

        # A default auth request we can use - un-scoped user token
        self.auth = self.build_authentication_request(
            user_id=self.user1['id'],
            password=self.user1['password'])

    def tearDown(self):
        super(IdentityTestFilteredCase, self).tearDown()
        rules.reset()
        self.opt(policy_file=self.orig_policy_file)

    def _get_id_list_from_ref_list(self, ref_list):
        result_list = []
        for x in ref_list:
            result_list.append(x['id'])
        return result_list

    def _set_policy(self, new_policy):
        with open(self.tmpfilename, "w") as policyfile:
            policyfile.write(jsonutils.dumps(new_policy))

    def test_list_users_filtered_by_domain(self):
        """GET /users?domain_id=mydomain (filtered)

        Test Plan:
        - Update policy so api is unprotected
        - Use an un-scoped token to make sure we can filter the
          users by domainB, getting back the 2 users in that domain

        """
        self._set_policy({"identity:list_users": []})
        url_by_name = '/users?domain_id=%s' % self.domainB['id']
        r = self.get(url_by_name, auth=self.auth)
        # We should  get back two users, those in DomainB
        id_list = self._get_id_list_from_ref_list(r.result.get('users'))
        self.assertIn(self.user2['id'], id_list)
        self.assertIn(self.user3['id'], id_list)

    def test_list_filtered_domains(self):
        """GET /domains?enabled=0

        Test Plan:
        - Update policy for no protection on api
        - Filter by the 'enabled' boolean to get disabled domains, which
          should return just domainC
        - Try the filter using different ways of specifying 'true'
          to test that our handling of booleans in filter matching is
          correct

        """
        new_policy = {"identity:list_domains": []}
        self._set_policy(new_policy)
        r = self.get('/domains?enabled=0', auth=self.auth)
        id_list = self._get_id_list_from_ref_list(r.result.get('domains'))
        self.assertEqual(len(id_list), 1)
        self.assertIn(self.domainC['id'], id_list)

        # Now try a few ways of specifying 'true' when we should get back
        # the other two domains, plus the default domain
        r = self.get('/domains?enabled=1', auth=self.auth)
        id_list = self._get_id_list_from_ref_list(r.result.get('domains'))
        self.assertEqual(len(id_list), 3)
        self.assertIn(self.domainA['id'], id_list)
        self.assertIn(self.domainB['id'], id_list)
        self.assertIn(DEFAULT_DOMAIN_ID, id_list)

        r = self.get('/domains?enabled', auth=self.auth)
        id_list = self._get_id_list_from_ref_list(r.result.get('domains'))
        self.assertEqual(len(id_list), 3)
        self.assertIn(self.domainA['id'], id_list)
        self.assertIn(self.domainB['id'], id_list)
        self.assertIn(DEFAULT_DOMAIN_ID, id_list)

    def test_multiple_filters(self):
        """GET /domains?enabled&name=myname

        Test Plan:
        - Update policy for no protection on api
        - Filter by the 'enabled' boolean and name - this should
          return a single domain

        """
        new_policy = {"identity:list_domains": []}
        self._set_policy(new_policy)

        my_url = '/domains?enableds&name=%s' % self.domainA['name']
        r = self.get(my_url, auth=self.auth)
        id_list = self._get_id_list_from_ref_list(r.result.get('domains'))
        self.assertEqual(len(id_list), 1)
        self.assertIn(self.domainA['id'], id_list)
