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
        # A number of other tests leave large numbers of entities (usually
        # users) lying around in the database, which would upset our pagination
        # tests, so clear out the users first.  It would obviously be a bad
        # thing if this were run against a live database, so put a sanity
        # check in to make sure there aren't a large number of entities.
        for entity in ['user', 'group', 'project']:
            entity_list = self._list_entities(entity)()
            self.assertTrue(len(entity_list) < 200)
            for item in entity_list:
                self._delete_entity(entity)(item['id'])

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

    def _check_links(self, link_dict, expected_dict):
        for link in ['previous', 'self', 'next']:
            if expected_dict[link] is None:
                self.assertEqual(link_dict[link], None)
            else:
                self.assertIn(expected_dict[link], link_dict[link])

    def test_list_entities_unpaginated(self):
        """GET /<entities> (unfiltered)

        Test Plan:
        - For each type of entity, do the following:
            - Update policy so api is unprotected
            - Create a whole bunch of users
            - list them back without asking for pagination, making sure we
              get them all back in one go and that the links are correct

        """
        for entity in ['user', 'group', 'project']:
            plural = '%ss' % entity
            self._set_policy({"identity:list_%s" % plural: []})

            # Create just a few more than the default page size
            entity_list = self._create_test_data(entity, 35)
            if entity == 'user':
                # Allow for the user we created in setUp
                entity_list.append(self.user1)

            list_url = '/%s' % plural
            entities = self.get(list_url, auth=self.auth)
            self._match_with_list(entities.result.get(plural), entity_list)
            self._check_links(
                entities.result['links'],
                {'previous': None, 'self': list_url, 'next': None})
            self.assertNotIn('page', entities.result['links']['self'])

            if entity == 'user':
                # Make sure we don't kill off the auth user
                entity_list.remove(self.user1)
            self._delete_test_data(entity, entity_list)

    def test_list_entities_paginated(self):
        """GET /<entities>?page (unfiltered)

        Test Plan:
        For each entity type:
            - Update policy so api is unprotected
            - Create a whole bunch of users
            - list them back explicitly page by page, checking we get them back
              in a consistent order with missing or duplicates
            - Then try just using the previous/next links to directly navigate
            - Finally change the page size, and ensure we get back pages that
              reflect this new size.

        """
        for entity in ['user', 'group', 'project']:
            plural = '%ss' % entity
            self._set_policy({"identity:list_%s" % plural: []})

            entity_list = self._create_test_data(entity, 65)
            sorted_entity_list = sorted(entity_list, key=lambda k: k['id'])

            # Start by explicitly going to each page
            list_url = '/%s?page=1' % plural
            entities = self.get(list_url, auth=self.auth)
            self._match_with_list(entities.result.get(plural),
                                  sorted_entity_list,
                                  list_start=0, list_end=30)
            self._check_links(
                entities.result['links'],
                {'previous': None, 'self': 'page=1', 'next': 'page=2'})

            list_url = '/%s?page=2' % plural
            entities = self.get(list_url, auth=self.auth)
            self._match_with_list(entities.result.get(plural),
                                  sorted_entity_list,
                                  list_start=30, list_end=60)
            self._check_links(
                entities.result['links'],
                {'previous': 'page=1', 'self': 'page=2', 'next': 'page=3'})

            list_url = '/%s?page=3' % plural
            entities = self.get(list_url, auth=self.auth)
            self._match_with_list(entities.result.get(plural),
                                  sorted_entity_list,
                                  batch_size=5, list_start=60, list_end=65)
            self._check_links(
                entities.result['links'],
                {'previous': 'page=2', 'self': 'page=3', 'next': None})

            # Now just use the links to go back through the pages
            entities = self.get(entities.result['links']['previous'],
                                auth=self.auth)
            self._match_with_list(entities.result.get(plural),
                                  sorted_entity_list,
                                  list_start=30, list_end=60)
            self._check_links(
                entities.result['links'],
                {'previous': 'page=1', 'self': 'page=2', 'next': 'page=3'})

            entities = self.get(entities.result['links']['previous'],
                                auth=self.auth)
            self._match_with_list(entities.result.get(plural),
                                  sorted_entity_list,
                                  list_start=0, list_end=30)
            self._check_links(
                entities.result['links'],
                {'previous': None, 'self': 'page=1', 'next': 'page=2'})

            # ...and back forward again...
            entities = self.get(entities.result['links']['next'],
                                auth=self.auth)
            self._match_with_list(entities.result.get(plural),
                                  sorted_entity_list,
                                  list_start=30, list_end=60)
            self._check_links(
                entities.result['links'],
                {'previous': 'page=1', 'self': 'page=2', 'next': 'page=3'})

            entities = self.get(entities.result['links']['next'],
                                auth=self.auth)
            self._match_with_list(entities.result.get(plural),
                                  sorted_entity_list,
                                  batch_size=5, list_start=60, list_end=65)
            self._check_links(
                entities.result['links'],
                {'previous': 'page=2', 'self': 'page=3', 'next': None})

            # Now change the page size, and make sure we get the first few
            # pages back correctly
            list_url = '/%s?page=1&per_page=10' % plural
            entities = self.get(list_url, auth=self.auth)
            self._match_with_list(entities.result.get(plural),
                                  sorted_entity_list,
                                  list_start=0, list_end=10)
            self._check_links(
                entities.result['links'],
                {'previous': None, 'self': 'page=1', 'next': 'page=2'})
            self._check_links(
                entities.result['links'],
                {'previous': None, 'self': 'per_page=10',
                 'next': 'per_page=10'})

            list_url = '/%s?page=2&per_page=10' % plural
            entities = self.get(list_url, auth=self.auth)
            self._match_with_list(entities.result.get(plural),
                                  sorted_entity_list,
                                  list_start=10, list_end=20)
            self._check_links(
                entities.result['links'],
                {'previous': 'page=1', 'self': 'page=2', 'next': 'page=3'})
            self._check_links(
                entities.result['links'],
                {'previous': 'per_page=10', 'self': 'per_page=10',
                 'next': 'per_page=10'})

            self._delete_test_data(entity, entity_list)
