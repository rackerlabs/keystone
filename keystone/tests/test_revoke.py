# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2014 OpenStack Foundation
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


import datetime

from keystone import config
from keystone.contrib import revoke
from keystone.contrib.revoke import model
from keystone.openstack.common import timeutils
from keystone import tests
from keystone.tests import test_backend_sql
import uuid


CONF = config.CONF


def _new_id():
    return uuid.uuid4()


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

    def test_past_expiry_are_removed(self):
        expire_delta = datetime.timedelta(seconds=1000)
        future_time = timeutils.utcnow() + expire_delta

        user_id = 1
        self.revoke_api.revoke_by_expiration(user_id, future_time)
        self.assertEqual(1, len(self.revoke_api.get_events()))

        expire_delta = datetime.timedelta(hours=-200)
        past_time = timeutils.utcnow() + expire_delta

        event = model.RevokeEvent()
        event.revoked_at = past_time
        self.revoke_api.revoke(event)
        self.assertEqual(1, len(self.revoke_api.get_events()))


class SqlRevokeTests(test_backend_sql.SqlTests, RevokeTests):
    def setUp(self):
        super(SqlRevokeTests, self).setUp()
        pass


class KvsRevokeTests(tests.TestCase, RevokeTests):
    def setUp(self):
        super(KvsRevokeTests, self).setUp()
        self.config([tests.dirs.etc('keystone.conf.sample'),
                     tests.dirs.tests(
                         'test_revoke_kvs.conf')])
        self.load_backends()
        self.revoke_api = revoke.Manager()


class RevokeTreeTests(tests.TestCase):
    def setUp(self):
        super(RevokeTreeTests, self).setUp()
        self.tree = model.RevokeTree()
        self._sample_data()

    def _sample_data(self):
        user_ids = []
        project_ids = []
        role_ids = []
        project_tokens = []
        for i in range(0, 3):
            user_ids.append(_new_id())
            project_ids.append(_new_id())
            role_ids.append(_new_id())

        project_tokens = []
        i = len(project_tokens)
        project_tokens.append(self._sample_blank_token())
        project_tokens[i]['user_id'] = user_ids[0]
        project_tokens[i]['project_id'] = project_ids[0]
        project_tokens[i]['roles'] = [role_ids[1]]

        i = len(project_tokens)
        project_tokens.append(self._sample_blank_token())
        project_tokens[i]['user_id'] = user_ids[1]
        project_tokens[i]['project_id'] = project_ids[0]
        project_tokens[i]['roles'] = [role_ids[0]]

        i = len(project_tokens)
        project_tokens.append(self._sample_blank_token())
        project_tokens[i]['user_id'] = user_ids[0]
        project_tokens[i]['project_id'] = project_ids[1]
        project_tokens[i]['roles'] = [role_ids[0]]

        token_to_revoke = self._sample_blank_token()
        token_to_revoke['user_id'] = user_ids[0]
        token_to_revoke['project_id'] = project_ids[0]
        token_to_revoke['roles'] = [role_ids[0]]

        self.project_tokens = project_tokens
        self.user_ids = user_ids
        self.project_ids = project_ids
        self.role_ids = role_ids
        self.token_to_revoke = token_to_revoke

    def tearDown(self):
        super(RevokeTreeTests, self).tearDown()
        pass

    def _assertTokenRevoked(self, token_data):
        return self.assertTrue(self.tree.is_revoked(token_data),
                               'Token should be revoked')

    def _assertTokenNotRevoked(self, token_data):
        return self.assertFalse(self.tree.is_revoked(token_data),
                                'Token should not be revoked')

    def _revoke_by_user(self, user_id):
        return self.tree.add_event(
            model.RevokeEvent(id=model.EventIdentifier(),
                              user_id=user_id))

    def _revoke_by_expiration(self, user_id, expires_at):
        return self.tree.add_event(
            model.RevokeEvent(id=model.EventIdentifier(),
                              user_id=user_id,
                              expires_at=expires_at))

    def _revoke_by_grant(self, role_id, user_id=None,
                         domain_id=None, project_id=None):
        return self.tree.add_event(
            model.RevokeEvent(id=model.EventIdentifier(),
                              user_id=user_id,
                              role_id=role_id,
                              domain_id=domain_id,
                              project_id=project_id))

    def _revoke_by_user_and_project(self, user_id, project_id):
        return self.tree.add_event(
            model.RevokeEvent(id=model.EventIdentifier(),
                              project_id=project_id,
                              user_id=user_id))

    def _revoke_by_project_role_assignment(self, project_id, role_id):
        return self.tree.add_event(
            model.RevokeEvent(id=model.EventIdentifier(),
                              project_id=project_id,
                              role_id=role_id))

    def _revoke_by_domain_role_assignment(self, domain_id, role_id):
            return self.tree.add_event(
                model.RevokeEvent(id=model.EventIdentifier(),
                                  domain_id=domain_id,
                                  role_id=role_id))

    def _sample_blank_token(self):
        issued_delta = datetime.timedelta(minutes=-2)
        issued_at = timeutils.utcnow() + issued_delta
        token_data = model.blank_token_data(issued_at)
        return token_data

    def _user_field_test(self, field_name):
        user_id = _new_id()
        event = self._revoke_by_user(user_id)
        token_data_u1 = self._sample_blank_token()
        token_data_u1[field_name] = user_id
        self._assertTokenRevoked(token_data_u1)
        token_data_u2 = self._sample_blank_token()
        token_data_u2[field_name] = _new_id()
        self._assertTokenNotRevoked(token_data_u2)
        self.tree.remove_event(event)
        self._assertTokenNotRevoked(token_data_u1)

    def test_revoke_by_user(self):
        self._user_field_test('user_id')

    def test_revoke_by_user_matches_trustee(self):
        self._user_field_test('trustee_id')

    def test_revoke_by_user_matches_trustor(self):
        self._user_field_test('trustor_id')

    def test_by_user_expiration(self):
        user_id = _new_id()
        future_time = _future_time()

        user_id = 1
        event = self._revoke_by_expiration(user_id, future_time)

        self._revoke_by_expiration(user_id, future_time)
        token_data_1 = self._sample_blank_token()
        token_data_1['user_id'] = user_id
        token_data_1['expires_at'] = future_time
        self._assertTokenRevoked(token_data_1)

        token_data_2 = self._sample_blank_token()
        token_data_2['user_id'] = user_id
        expire_delta = datetime.timedelta(seconds=2000)
        future_time = timeutils.utcnow() + expire_delta
        token_data_2['expires_at'] = future_time
        self._assertTokenNotRevoked(token_data_2)

        self.tree.remove_event(event)
        self._assertTokenNotRevoked(token_data_1)

    def test_by_project_grant(self):
        token_to_revoke = self.token_to_revoke
        tokens = self.project_tokens

        self._assertTokenNotRevoked(token_to_revoke)
        for token in tokens:
            self._assertTokenNotRevoked(token)

        event = self._revoke_by_grant(role_id=self.role_ids[0],
                                      user_id=self.user_ids[0],
                                      project_id=self.project_ids[0])

        self._assertTokenRevoked(token_to_revoke)
        for token in tokens:
            self._assertTokenNotRevoked(token)

        self.tree.remove_event(event)

        self._assertTokenNotRevoked(token_to_revoke)
        for token in tokens:
            self._assertTokenNotRevoked(token)

        token_to_revoke['roles'] = [self.role_ids[0],
                                    self.role_ids[1],
                                    self.role_ids[2]]

        event = self._revoke_by_grant(role_id=self.role_ids[0],
                                      user_id=self.user_ids[0],
                                      project_id=self.project_ids[0])
        self._assertTokenRevoked(token_to_revoke)
        self.tree.remove_event(event)
        self._assertTokenNotRevoked(token_to_revoke)

        event = self._revoke_by_grant(role_id=self.role_ids[1],
                                      user_id=self.user_ids[0],
                                      project_id=self.project_ids[0])
        self._assertTokenRevoked(token_to_revoke)
        self.tree.remove_event(event)
        self._assertTokenNotRevoked(token_to_revoke)

        self._revoke_by_grant(role_id=self.role_ids[0],
                              user_id=self.user_ids[0],
                              project_id=self.project_ids[0])
        self._revoke_by_grant(role_id=self.role_ids[1],
                              user_id=self.user_ids[0],
                              project_id=self.project_ids[0])
        self._revoke_by_grant(role_id=self.role_ids[2],
                              user_id=self.user_ids[0],
                              project_id=self.project_ids[0])
        self._assertTokenRevoked(token_to_revoke)

    def _assertEmpty(self, collection):
        return self.assertEqual(0, len(collection), "collection not empty")

    def _assertEventsMatchIteration(self, iter):
        self.assertEqual(1, len(self.tree.revoke_map))
        self.assertEqual(iter + 1, len(self.tree.revoke_map
                                       ['trust_id=None']
                                       ['consumer_id=None']
                                       ['access_token_id=None']))
    #two different functions add  domain_ids, +1 for None
        self.assertEqual(2 * iter + 1, len(self.tree.revoke_map
                                           ['trust_id=None']
                                           ['consumer_id=None']
                                           ['access_token_id=None']
                                           ['expires_at=None']))
    #two different functions add  project_ids, +1 for None
        self.assertEqual(2 * iter + 1, len(self.tree.revoke_map
                                           ['trust_id=None']
                                           ['consumer_id=None']
                                           ['access_token_id=None']
                                           ['expires_at=None']
                                           ['domain_id=None']))
    #10 users added
        self.assertEqual(iter, len(self.tree.revoke_map
                                   ['trust_id=None']
                                   ['consumer_id=None']
                                   ['access_token_id=None']
                                   ['expires_at=None']
                                   ['domain_id=None']
                                   ['project_id=None']))

    def test_cleanup(self):
        events = []
        self._assertEmpty(self.tree.revoke_map)
        for i in range(0, 10):
            events.append(
                self._revoke_by_user(_new_id()))
            events.append(
                self._revoke_by_expiration(_new_id(), _future_time()))
            events.append(
                self._revoke_by_project_role_assignment(_new_id(), _new_id()))
            events.append(
                self._revoke_by_domain_role_assignment(_new_id(), _new_id()))
            events.append(
                self._revoke_by_domain_role_assignment(_new_id(), _new_id()))
            events.append(
                self._revoke_by_user_and_project(_new_id(), _new_id()))
            self._assertEventsMatchIteration(i + 1)

        for event in events:
            self.tree.remove_event(event)
        self._assertEmpty(self.tree.revoke_map)
