# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack Foundation
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
from keystone.contrib import revoke
from keystone.openstack.common import timeutils
from keystone import tests
from keystone.tests import test_backend_sql


CONF = config.CONF


class RevokeTests(object):

    def test_list(self):
        valid_until = timeutils.utcnow()
        REVOKE_EVENT_A = revoke.RevokeEvent(id="a",
                                            scope_id="1",
                                            scope_type=1,
                                            valid_until=valid_until)
        REVOKE_EVENT_B = revoke.RevokeEvent(id="b",
                                            scope_id="2",
                                            scope_type=2,
                                            valid_until=valid_until)

        self.revoke_api.revoke(REVOKE_EVENT_A)
        self.assertEquals(1, len(self.revoke_api.get_events()))

        self.revoke_api.revoke(REVOKE_EVENT_B)
        self.assertEquals(2, len(self.revoke_api.get_events()))

    def assertSortedByScopeId(self, events):
        cur = 0
        nxt = 1
        while nxt < len(events):
            self.assertLess(events[cur].scope_id, events[nxt].scope_id)
            cur += 1
            nxt += 1

    def test_list_is_sorted(self):
        valid_until = timeutils.utcnow()
        events = self.revoke_api.get_events()
        start_count = len(events)
        for id in range(0, 8):
            self.revoke_api.revoke(revoke.RevokeEvent(
                id="%d" % id,
                scope_id=uuid.uuid4().__str__(),
                scope_type=1,
                valid_until=valid_until))
        count = id + 1
        count += start_count
        events = self.revoke_api.get_events()
        self.assertEquals(count, len(events))
        self.assertSortedByScopeId(events)


class SqlRevokeTests(test_backend_sql.SqlTests, RevokeTests):
    def setUp(self):
        super(SqlRevokeTests, self).setUp()
        self.revoke_api = revoke.Manager()


class KvsRevokeTests(tests.TestCase, RevokeTests):
    def setUp(self):
        super(KvsRevokeTests, self).setUp()
        self.revoke_api = revoke.Manager()
        self.revoke_api.driver._clear()
