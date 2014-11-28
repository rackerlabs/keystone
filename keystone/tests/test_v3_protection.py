# Copyright 2012 OpenStack Foundation
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

import uuid

from oslo.serialization import jsonutils

from keystone import config
from keystone import exception
from keystone.policy.backends import rules
from keystone.tests.ksfixtures import temporaryfile
from keystone.tests import test_v3


CONF = config.CONF
DEFAULT_DOMAIN_ID = CONF.identity.default_domain_id


class IdentityTestProtectedCase(test_v3.RestfulTestCase):
    """Test policy enforcement on the v3 Identity API."""

    def setUp(self):
        """Setup for Identity Protection Test Cases.

        As well as the usual housekeeping, create a set of domains,
        users, roles and projects for the subsequent tests:

        - Three domains: A,B & C.  C is disabled.
        - DomainA has user1, DomainB has user2 and user3
        - DomainA has group1 and group2, DomainB has group3
        - User1 has two roles on DomainA
        - User2 has one role on DomainA

        Remember that there will also be a fourth domain in existence,
        the default domain.

        """
        # Ensure that test_v3.RestfulTestCase doesn't load its own
        # sample data, which would make checking the results of our
        # tests harder
        super(IdentityTestProtectedCase, self).setUp()

        # Initialize the policy engine and allow us to write to a temp
        # file in each test to create the policies
        self.addCleanup(rules.reset)
        rules.reset()
        self.tempfile = self.useFixture(temporaryfile.SecureTempFile())
        self.tmpfilename = self.tempfile.file_name
        self.config_fixture.config(policy_file=self.tmpfilename)

        # A default auth request we can use - un-scoped user token
        self.auth = self.build_authentication_request(
            user_id=self.user1['id'],
            password=self.user1['password'])

    def load_sample_data(self):
        self._populate_default_domain()
        # Start by creating a couple of domains
        self.domainA = self.new_domain_ref()
        self.assignment_api.create_domain(self.domainA['id'], self.domainA)
        self.domainB = self.new_domain_ref()
        self.assignment_api.create_domain(self.domainB['id'], self.domainB)
        self.domainC = self.new_domain_ref()
        self.domainC['enabled'] = False
        self.assignment_api.create_domain(self.domainC['id'], self.domainC)

        # Now create some users, one in domainA and two of them in domainB
        self.user1 = self.new_user_ref(domain_id=self.domainA['id'])
        password = uuid.uuid4().hex
        self.user1['password'] = password
        self.user1 = self.identity_api.create_user(self.user1)
        self.user1['password'] = password

        self.user2 = self.new_user_ref(domain_id=self.domainB['id'])
        password = uuid.uuid4().hex
        self.user2['password'] = password
        self.user2 = self.identity_api.create_user(self.user2)
        self.user2['password'] = password

        self.user3 = self.new_user_ref(domain_id=self.domainB['id'])
        password = uuid.uuid4().hex
        self.user3['password'] = password
        self.user3 = self.identity_api.create_user(self.user3)
        self.user3['password'] = password

        self.group1 = self.new_group_ref(domain_id=self.domainA['id'])
        self.group1 = self.identity_api.create_group(self.group1)

        self.group2 = self.new_group_ref(domain_id=self.domainA['id'])
        self.group2 = self.identity_api.create_group(self.group2)

        self.group3 = self.new_group_ref(domain_id=self.domainB['id'])
        self.group3 = self.identity_api.create_group(self.group3)

        self.role = self.new_role_ref()
        self.assignment_api.create_role(self.role['id'], self.role)
        self.role1 = self.new_role_ref()
        self.assignment_api.create_role(self.role1['id'], self.role1)
        self.assignment_api.create_grant(self.role['id'],
                                         user_id=self.user1['id'],
                                         domain_id=self.domainA['id'])
        self.assignment_api.create_grant(self.role['id'],
                                         user_id=self.user2['id'],
                                         domain_id=self.domainA['id'])
        self.assignment_api.create_grant(self.role1['id'],
                                         user_id=self.user1['id'],
                                         domain_id=self.domainA['id'])

    def _get_id_list_from_ref_list(self, ref_list):
        result_list = []
        for x in ref_list:
            result_list.append(x['id'])
        return result_list

    def _set_policy(self, new_policy):
        with open(self.tmpfilename, "w") as policyfile:
            policyfile.write(jsonutils.dumps(new_policy))

    def test_list_users_unprotected(self):
        """GET /users (unprotected)

        Test Plan:

        - Update policy so api is unprotected
        - Use an un-scoped token to make sure we can get back all
          the users independent of domain

        """
        self._set_policy({"identity:list_users": []})
        r = self.get('/users', auth=self.auth)
        id_list = self._get_id_list_from_ref_list(r.result.get('users'))
        self.assertIn(self.user1['id'], id_list)
        self.assertIn(self.user2['id'], id_list)
        self.assertIn(self.user3['id'], id_list)

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

    def test_get_user_protected_match_id(self):
        """GET /users/{id} (match payload)

        Test Plan:

        - Update policy to protect api by user_id
        - List users with user_id of user1 as filter, to check that
          this will correctly match user_id in the flattened
          payload

        """
        # TODO(henry-nash, ayoung): It would be good to expand this
        # test for further test flattening, e.g. protect on, say, an
        # attribute of an object being created
        new_policy = {"identity:get_user": [["user_id:%(user_id)s"]]}
        self._set_policy(new_policy)
        url_by_name = '/users/%s' % self.user1['id']
        r = self.get(url_by_name, auth=self.auth)
        self.assertEqual(self.user1['id'], r.result['user']['id'])

    def test_get_user_protected_match_target(self):
        """GET /users/{id} (match target)

        Test Plan:

        - Update policy to protect api by domain_id
        - Try and read a user who is in DomainB with a token scoped
          to Domain A - this should fail
        - Retry this for a user who is in Domain A, which should succeed.
        - Finally, try getting a user that does not exist, which should
          still return UserNotFound

        """
        new_policy = {'identity:get_user':
                      [["domain_id:%(target.user.domain_id)s"]]}
        self._set_policy(new_policy)
        self.auth = self.build_authentication_request(
            user_id=self.user1['id'],
            password=self.user1['password'],
            domain_id=self.domainA['id'])
        url_by_name = '/users/%s' % self.user2['id']
        r = self.get(url_by_name, auth=self.auth,
                     expected_status=exception.ForbiddenAction.code)

        url_by_name = '/users/%s' % self.user1['id']
        r = self.get(url_by_name, auth=self.auth)
        self.assertEqual(self.user1['id'], r.result['user']['id'])

        url_by_name = '/users/%s' % uuid.uuid4().hex
        r = self.get(url_by_name, auth=self.auth,
                     expected_status=exception.UserNotFound.code)

    def test_revoke_grant_protected_match_target(self):
        """DELETE /domains/{id}/users/{id}/roles/{id} (match target)

        Test Plan:

        - Update policy to protect api by domain_id of entities in
          the grant
        - Try and delete the existing grant that has a user who is
          from a different domain - this should fail.
        - Retry this for a user who is in Domain A, which should succeed.

        """
        new_policy = {'identity:revoke_grant':
                      [["domain_id:%(target.user.domain_id)s"]]}
        self._set_policy(new_policy)
        collection_url = (
            '/domains/%(domain_id)s/users/%(user_id)s/roles' % {
                'domain_id': self.domainA['id'],
                'user_id': self.user2['id']})
        member_url = '%(collection_url)s/%(role_id)s' % {
            'collection_url': collection_url,
            'role_id': self.role['id']}

        self.auth = self.build_authentication_request(
            user_id=self.user1['id'],
            password=self.user1['password'],
            domain_id=self.domainA['id'])
        self.delete(member_url, auth=self.auth,
                    expected_status=exception.ForbiddenAction.code)

        collection_url = (
            '/domains/%(domain_id)s/users/%(user_id)s/roles' % {
                'domain_id': self.domainA['id'],
                'user_id': self.user1['id']})
        member_url = '%(collection_url)s/%(role_id)s' % {
            'collection_url': collection_url,
            'role_id': self.role1['id']}
        self.delete(member_url, auth=self.auth)

    def test_list_users_protected_by_domain(self):
        """GET /users?domain_id=mydomain (protected)

        Test Plan:

        - Update policy to protect api by domain_id
        - List groups using a token scoped to domainA with a filter
          specifying domainA - we should only get back the one user
          that is in domainA.
        - Try and read the users from domainB - this should fail since
          we don't have a token scoped for domainB

        """
        new_policy = {"identity:list_users": ["domain_id:%(domain_id)s"]}
        self._set_policy(new_policy)
        self.auth = self.build_authentication_request(
            user_id=self.user1['id'],
            password=self.user1['password'],
            domain_id=self.domainA['id'])
        url_by_name = '/users?domain_id=%s' % self.domainA['id']
        r = self.get(url_by_name, auth=self.auth)
        # We should only get back one user, the one in DomainA
        id_list = self._get_id_list_from_ref_list(r.result.get('users'))
        self.assertEqual(1, len(id_list))
        self.assertIn(self.user1['id'], id_list)

        # Now try for domainB, which should fail
        url_by_name = '/users?domain_id=%s' % self.domainB['id']
        r = self.get(url_by_name, auth=self.auth,
                     expected_status=exception.ForbiddenAction.code)

    def test_list_groups_protected_by_domain(self):
        """GET /groups?domain_id=mydomain (protected)

        Test Plan:

        - Update policy to protect api by domain_id
        - List groups using a token scoped to domainA and make sure
          we only get back the two groups that are in domainA
        - Try and read the groups from domainB - this should fail since
          we don't have a token scoped for domainB

        """
        new_policy = {"identity:list_groups": ["domain_id:%(domain_id)s"]}
        self._set_policy(new_policy)
        self.auth = self.build_authentication_request(
            user_id=self.user1['id'],
            password=self.user1['password'],
            domain_id=self.domainA['id'])
        url_by_name = '/groups?domain_id=%s' % self.domainA['id']
        r = self.get(url_by_name, auth=self.auth)
        # We should only get back two groups, the ones in DomainA
        id_list = self._get_id_list_from_ref_list(r.result.get('groups'))
        self.assertEqual(2, len(id_list))
        self.assertIn(self.group1['id'], id_list)
        self.assertIn(self.group2['id'], id_list)

        # Now try for domainB, which should fail
        url_by_name = '/groups?domain_id=%s' % self.domainB['id']
        r = self.get(url_by_name, auth=self.auth,
                     expected_status=exception.ForbiddenAction.code)

    def test_list_groups_protected_by_domain_and_filtered(self):
        """GET /groups?domain_id=mydomain&name=myname (protected)

        Test Plan:

        - Update policy to protect api by domain_id
        - List groups using a token scoped to domainA with a filter
          specifying both domainA and the name of group.
        - We should only get back the group in domainA that matches
          the name

        """
        new_policy = {"identity:list_groups": ["domain_id:%(domain_id)s"]}
        self._set_policy(new_policy)
        self.auth = self.build_authentication_request(
            user_id=self.user1['id'],
            password=self.user1['password'],
            domain_id=self.domainA['id'])
        url_by_name = '/groups?domain_id=%s&name=%s' % (
            self.domainA['id'], self.group2['name'])
        r = self.get(url_by_name, auth=self.auth)
        # We should only get back one user, the one in DomainA that matches
        # the name supplied
        id_list = self._get_id_list_from_ref_list(r.result.get('groups'))
        self.assertEqual(1, len(id_list))
        self.assertIn(self.group2['id'], id_list)
