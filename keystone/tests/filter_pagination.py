# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack LLC
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

from keystone import config

CONF = config.CONF
DEFAULT_DOMAIN_ID = CONF.identity.default_domain_id


class FilterPaginationTests(object):
    _user_list = []

    def tearDown(self):
        super(FilterPaginationTests, self).tearDown()
#        self._delete_user_data()

    def _delete_user_data(self):
        for user in self._user_list:
            self.identity_api.delete_user(user['id'])

    def _match_with_list(self, this_batch, total_list,
                         batch_size=None,
                         list_start=None, list_end=None):
        if batch_size is None:
            batch_size = len(this_batch)
        if list_start is None:
            list_start = 0
        if list_end is None:
            list_end = len(total_list)
        for batch_item in range(0, batch_size):
            found = False
            for list_item in range(list_start, list_end):
                if this_batch[batch_item]['id'] == total_list[list_item]['id']:
                    found = True
            self.assertTrue(found)

    def _create_user(self, domain_id):
        # Make sure our user.id's will order before any of the default
        # fixtures
        new_user = {'id': '0000' + uuid.uuid4().hex,
                    'name': uuid.uuid4().hex,
                    'password': uuid.uuid4().hex, 'enabled': True,
                    'domain_id': domain_id}
        self.identity_api.create_user(new_user['id'], new_user)
        return new_user

    def _create_user_data(self, total, domain_id=None, split=None):
        """Create user test data, in one or two batches

        :param total: total number of users to create,
        :param domain_id: if not defined, all users will be created in the
                          default domain. If specified, this gives the
                          domain_id for the second batch
        :param split: the dividing line in terms of numbers that go into batch
                      one or two.  Users above split go into batch two.

        If a second batch was created, return a list of the users in that
        batch, else return a list of all users

        """
        if self._user_list:
            self._delete_user_data()
        self._user_list = []
        batch_list = []

        for x in range(total):
            if domain_id is not None and x > split:
                the_domain_id = domain_id
            else:
                the_domain_id = DEFAULT_DOMAIN_ID

            new_user = self._create_user(the_domain_id)
            self._user_list.append(new_user)
            if domain_id is not None:
                if domain_id == the_domain_id:
                    batch_list.append(new_user)
        if domain_id is not None:
            return batch_list
        else:
            return self._user_list
