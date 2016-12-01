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

import keystone.conf
from keystone import exception
from keystone.tests import unit
from keystone.tests.unit import test_v3


CONF = keystone.conf.CONF


class DuplicateTestCase(test_v3.RestfulTestCase, unit.TestCase):
    def test_user_duplicate_conflict_gives_name(self):
        user = unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        user = self.identity_api.create_user(user)
        try:
            self.identity_api.create_user(user)
        except exception.Conflict as e:
            self.assertIn("Duplicate entry found with name %s" % user['name'],
                          unicode(e))
        else:
            self.fail("Create role_domain did not raise a conflict")

    def test_role_duplicate_conflict_gives_name(self):
        role = unit.new_role_ref(id='fake1', name='fake1name')
        self.role_api.create_role('fake1', role)
        role['id'] = 'fake2'
        try:
            self.role_api.create_role(role['id'], role)
        except exception.Conflict as e:
            self.assertIn("Duplicate entry found with name %s" % role['name'],
                          unicode(e))
        else:
            self.fail("Create role_domain did not raise a conflict")

    def test_group_duplicate_conflict_gives_name(self):
        group1 = unit.new_group_ref(domain_id=CONF.identity.default_domain_id)
        group2 = unit.new_group_ref(domain_id=CONF.identity.default_domain_id,
                                    name=group1['name'])
        group1 = self.identity_api.create_group(group1)
        try:
            self.identity_api.create_group(group2)
        except exception.Conflict as e:
            self.assertIn("Duplicate entry found with name %s"
                          % group2['name'], unicode(e))
        else:
            self.fail("Create role_domain did not raise a conflict")
