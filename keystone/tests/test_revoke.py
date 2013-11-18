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

from keystone import config
from keystone.tests import test_backend_sql


from keystone.contrib import revoke
from keystone import tests

CONF = config.CONF


class RevokeTests(object):

    def test_list(self):
        self.revoke_api.revoke(revoke.RevokeEvent(id="a",
                                                  scope_id="1",
                                                  scope_type=1,
                                                  expires_net=None,
                                                  expires_nlt=None))
        self.assertEquals(1, len(self.revoke_api.get_events()))

        self.revoke_api.revoke(revoke.RevokeEvent(id="b",
                                                  scope_id="2",
                                                  scope_type=2,
                                                  expires_net=None,
                                                  expires_nlt=None))
        self.assertEquals(2, len(self.revoke_api.get_events()))


class SqlRevokeTests(test_backend_sql.SqlTests, RevokeTests):
    def setUp(self):
        super(SqlRevokeTests, self).setUp()
        self.revoke_api = revoke.Manager()


class KvsRevokeTests(tests.TestCase, RevokeTests):
    def setUp(self):
        super(KvsRevokeTests, self).setUp()
        self.revoke_api = revoke.Manager()
