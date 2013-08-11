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

import filter_pagination
import test_v3


CONF = config.CONF
DEFAULT_DOMAIN_ID = CONF.identity.default_domain_id


class IdentityTestPaginationCase(test_v3.RestfulTestCase,
                                 filter_pagination.FilterPaginationTests):
    """Test pagination enforcement on the v3 Identity API."""

    def setUp(self):
        # Ensure that test_v3.RestfulTestCase doesn't load its own
        # sample data, which would make checking the results of our
        # tests harder
        super(IdentityTestPaginationCase, self).setUp(load_sample_data=False)
        # A number of other tests leave large numbers of users lying around in
        # the database, which would upset our pagination tests, so clear out
        # the users first.  It would obviously be a bad thing if this were
        # run against a live database.
        for user in self.identity_api.list_users():
            self.identity_api.delete_user(user['id'])
        self.domainA = self.new_domain_ref()
        self.identity_api.create_domain(self.domainA['id'], self.domainA)
        self.user1 = self.new_user_ref(domain_id=self.domainA['id'])
        self.user1['password'] = uuid.uuid4().hex
        self.identity_api.create_user(self.user1['id'], self.user1)
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
        super(IdentityTestPaginationCase, self).tearDown()
        rules.reset()
        self.opt(policy_file=self.orig_policy_file)

    def _set_policy(self, new_policy):
        with open(self.tmpfilename, "w") as policyfile:
            policyfile.write(jsonutils.dumps(new_policy))

    def test_list_users_paginated(self):
        """GET /users?page (unfiltered)

        Test Plan:
        - Update policy so api is unprotected
        - Create a whole bunch of users
        - list them back explicitly page by page, checking we get them back in
          a consistent order with missing or duplicates
        - Then try just using the previous/next links to directly navigate
        - Finally change the page size, and ensure we get back pages that
        reflect this new size.

        """
        def check_links(link_dict, expected_dict):
            for link in ['previous', 'self', 'next']:
                if expected_dict[link] is None:
                    self.assertEqual(link_dict[link], None)
                else:
                    self.assertIn(expected_dict[link], link_dict[link])

        user_list = self._create_user_data(65)
        sorted_user_list = sorted(user_list, key=lambda k: k['id'])

        self._set_policy({"identity:list_users": []})

        # Start by explicitly going to each page
        url_by_name = '/users?page=1'
        users = self.get(url_by_name, auth=self.auth)
        self._match_with_list(users.result.get('users'), sorted_user_list,
                              list_start=0, list_end=30)
        check_links(users.result['links'],
                    {'previous': None, 'self': 'page=1', 'next': 'page=2'})

        url_by_name = '/users?page=2'
        users = self.get(url_by_name, auth=self.auth)
        self._match_with_list(users.result.get('users'), sorted_user_list,
                              list_start=30, list_end=60)
        check_links(users.result['links'],
                    {'previous': 'page=1', 'self': 'page=2', 'next': 'page=3'})

        url_by_name = '/users?page=3'
        users = self.get(url_by_name, auth=self.auth)
        self._match_with_list(users.result.get('users'), sorted_user_list,
                              batch_size=5, list_start=60, list_end=65)
        check_links(users.result['links'],
                    {'previous': 'page=2', 'self': 'page=3', 'next': None})

        # Now just use the links to go back through the pages
        users = self.get(users.result['links']['previous'], auth=self.auth)
        self._match_with_list(users.result.get('users'), sorted_user_list,
                              list_start=30, list_end=60)
        check_links(users.result['links'],
                    {'previous': 'page=1', 'self': 'page=2', 'next': 'page=3'})

        users = self.get(users.result['links']['previous'], auth=self.auth)
        self._match_with_list(users.result.get('users'), sorted_user_list,
                              list_start=0, list_end=30)
        check_links(users.result['links'],
                    {'previous': None, 'self': 'page=1', 'next': 'page=2'})

        # ...and back forward again...
        users = self.get(users.result['links']['next'], auth=self.auth)
        self._match_with_list(users.result.get('users'), sorted_user_list,
                              list_start=30, list_end=60)
        check_links(users.result['links'],
                    {'previous': 'page=1', 'self': 'page=2', 'next': 'page=3'})

        users = self.get(users.result['links']['next'], auth=self.auth)
        self._match_with_list(users.result.get('users'), sorted_user_list,
                              batch_size=5, list_start=60, list_end=65)
        check_links(users.result['links'],
                    {'previous': 'page=2', 'self': 'page=3', 'next': None})

        # Now change the page size, and make sure we get the first few pages
        # back correctly
        url_by_name = '/users?page=1&per_page=10'
        users = self.get(url_by_name, auth=self.auth)
        self._match_with_list(users.result.get('users'), sorted_user_list,
                              list_start=0, list_end=10)
        check_links(
            users.result['links'],
            {'previous': None, 'self': 'page=1', 'next': 'page=2'})
        check_links(
            users.result['links'],
            {'previous': None, 'self': 'per_page=10', 'next': 'per_page=10'})

        url_by_name = '/users?page=2&per_page=10'
        users = self.get(url_by_name, auth=self.auth)
        self._match_with_list(users.result.get('users'), sorted_user_list,
                              list_start=10, list_end=20)
        check_links(
            users.result['links'],
            {'previous': 'page=1', 'self': 'page=2', 'next': 'page=3'})
        check_links(
            users.result['links'],
            {'previous': 'per_page=10', 'self': 'per_page=10',
             'next': 'per_page=10'})
