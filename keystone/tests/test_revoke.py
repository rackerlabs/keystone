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


import datetime

from keystone.common import dependency
from keystone import config
from keystone.contrib.revoke import model
from keystone.openstack.common import timeutils
from keystone import tests


CONF = config.CONF


def _future_time():
    expire_delta = datetime.timedelta(seconds=1000)
    future_time = timeutils.utcnow() + expire_delta
    return future_time


class RevokeTests(object):

    def test_list(self):
        self.revoke_api.revoke_by_user(user_id=1)
        self.assertEqual(1, len(self.revoke_api.get_events()))

        self.revoke_api.revoke_by_user(user_id=2)
        self.assertEqual(2, len(self.revoke_api.get_events()))

    def test_list_since(self):
        self.revoke_api.revoke_by_user(user_id=1)
        self.revoke_api.revoke_by_user(user_id=2)
        past = timeutils.utcnow() - datetime.timedelta(seconds=1000)
        self.assertEqual(2, len(self.revoke_api.get_events(past)))
        future = timeutils.utcnow() + datetime.timedelta(seconds=1000)
        self.assertEqual(0, len(self.revoke_api.get_events(future)))

    def _past_time(self):
        expire_delta = datetime.timedelta(days=-1000)
        past_time = timeutils.utcnow() + expire_delta
        return past_time

    def test_past_expiry_are_removed(self):
        user_id = 1
        self.revoke_api.revoke_by_expiration(user_id, _future_time())
        self.assertEqual(1, len(self.revoke_api.get_events()))

        event = model.RevokeEvent()
        event.revoked_at = self._past_time()
        self.revoke_api.revoke(event)
        self.assertEqual(1, len(self.revoke_api.get_events()))


@dependency.requires('revoke_api')
class KvsRevokeTests(tests.TestCase, RevokeTests):
    def setUp(self):
        super(KvsRevokeTests, self).setUp()
        self.config([tests.dirs.etc('keystone.conf.sample'),
                     tests.dirs.tests(
                         'test_token_provider_revoke_by_id_false.conf')])
        self.load_backends()
