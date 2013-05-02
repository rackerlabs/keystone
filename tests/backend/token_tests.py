# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack LLC
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
import datetime
from keystone import exception
from keystone.openstack.common import timeutils


class TokenTests(object):
    def _create_token_id(self):
        # Token must start with MII here otherwise it fails the asn1 test
        # and is not hashed in a SQL backend.
        token_id = "MII"
        for i in range(1, 20):
            token_id += uuid.uuid4().hex
        return token_id

    def test_token_crud(self):
        token_id = self._create_token_id()
        data = {'id': token_id, 'a': 'b',
                'trust_id': None,
                'user': {'id': 'testuserid'}}
        data_ref = self.token_api.create_token(token_id, data)
        expires = data_ref.pop('expires')
        self.assertTrue(isinstance(expires, datetime.datetime))
        self.assertEquals(data['trust_id'], data_ref['trust_id'])
        self.assertEquals(data['user'], data_ref['user'])

        new_data_ref = self.token_api.get_token(token_id)
        self.assertTrue(isinstance(new_data_ref['expires'], datetime.datetime))
        self.assertEquals(data['trust_id'], new_data_ref['trust_id'])
        self.assertEquals(data['user'], new_data_ref['user'])

        self.token_api.delete_token(token_id)
        self.assertRaises(exception.TokenNotFound,
                          self.token_api.get_token, token_id)
        self.assertRaises(exception.TokenNotFound,
                          self.token_api.delete_token, token_id)

    def create_token_sample_data(self, tenant_id=None, trust_id=None):
        token_id = self._create_token_id()
        data = {'id': token_id, 'a': 'b',
                'user': {'id': 'testuserid'}}
        if tenant_id is not None:
            data['tenant'] = {'id': tenant_id, 'name': tenant_id}
        if trust_id is not None:
            data['trust_id'] = trust_id
        new_token = self.token_api.create_token(token_id, data)
        return new_token['id']

    def test_token_list(self):
        tokens = self.token_api.list_tokens('testuserid')
        self.assertEquals(len(tokens), 0)
        token_id1 = self.create_token_sample_data()
        tokens = self.token_api.list_tokens('testuserid')
        self.assertEquals(len(tokens), 1)
        self.assertIn(token_id1, tokens)
        token_id2 = self.create_token_sample_data()
        tokens = self.token_api.list_tokens('testuserid')
        self.assertEquals(len(tokens), 2)
        self.assertIn(token_id2, tokens)
        self.assertIn(token_id1, tokens)
        self.token_api.delete_token(token_id1)
        tokens = self.token_api.list_tokens('testuserid')
        self.assertIn(token_id2, tokens)
        self.assertNotIn(token_id1, tokens)
        self.token_api.delete_token(token_id2)
        tokens = self.token_api.list_tokens('testuserid')
        self.assertNotIn(token_id2, tokens)
        self.assertNotIn(token_id1, tokens)

        # tenant-specific tokens
        tenant1 = uuid.uuid4().hex
        tenant2 = uuid.uuid4().hex
        token_id3 = self.create_token_sample_data(tenant_id=tenant1)
        token_id4 = self.create_token_sample_data(tenant_id=tenant2)
        tokens = self.token_api.list_tokens('testuserid')
        self.assertEquals(len(tokens), 2)
        self.assertNotIn(token_id1, tokens)
        self.assertNotIn(token_id2, tokens)
        self.assertIn(token_id3, tokens)
        self.assertIn(token_id4, tokens)
        tokens = self.token_api.list_tokens('testuserid', tenant2)
        self.assertEquals(len(tokens), 1)
        self.assertNotIn(token_id1, tokens)
        self.assertNotIn(token_id2, tokens)
        self.assertNotIn(token_id3, tokens)
        self.assertIn(token_id4, tokens)

    def test_token_list_trust(self):
        trust_id = uuid.uuid4().hex
        token_id5 = self.create_token_sample_data(trust_id=trust_id)
        tokens = self.token_api.list_tokens('testuserid', trust_id=trust_id)
        self.assertEquals(len(tokens), 1)
        self.assertIn(token_id5, tokens)

    def test_get_token_404(self):
        self.assertRaises(exception.TokenNotFound,
                          self.token_api.get_token,
                          uuid.uuid4().hex)
        self.assertRaises(exception.TokenNotFound,
                          self.token_api.get_token,
                          None)

    def test_delete_token_404(self):
        self.assertRaises(exception.TokenNotFound,
                          self.token_api.delete_token,
                          uuid.uuid4().hex)

    def test_expired_token(self):
        token_id = uuid.uuid4().hex
        expire_time = timeutils.utcnow() - datetime.timedelta(minutes=1)
        data = {'id_hash': token_id, 'id': token_id, 'a': 'b',
                'expires': expire_time,
                'trust_id': None,
                'user': {'id': 'testuserid'}}
        data_ref = self.token_api.create_token(token_id, data)
        data_ref.pop('user_id')
        self.assertDictEqual(data_ref, data)
        self.assertRaises(exception.TokenNotFound,
                          self.token_api.get_token, token_id)

    def test_null_expires_token(self):
        token_id = uuid.uuid4().hex
        data = {'id': token_id, 'id_hash': token_id, 'a': 'b', 'expires': None,
                'user': {'id': 'testuserid'}}
        data_ref = self.token_api.create_token(token_id, data)
        self.assertIsNotNone(data_ref['expires'])
        new_data_ref = self.token_api.get_token(token_id)
        self.assertEqual(data_ref, new_data_ref)

    def check_list_revoked_tokens(self, token_ids):
        revoked_ids = [x['id'] for x in self.token_api.list_revoked_tokens()]
        for token_id in token_ids:
            self.assertIn(token_id, revoked_ids)

    def delete_token(self):
        token_id = uuid.uuid4().hex
        data = {'id_hash': token_id, 'id': token_id, 'a': 'b',
                'user': {'id': 'testuserid'}}
        data_ref = self.token_api.create_token(token_id, data)
        self.token_api.delete_token(token_id)
        self.assertRaises(
            exception.TokenNotFound,
            self.token_api.get_token,
            data_ref['id'])
        self.assertRaises(
            exception.TokenNotFound,
            self.token_api.delete_token,
            data_ref['id'])
        return token_id

    def test_list_revoked_tokens_returns_empty_list(self):
        revoked_ids = [x['id'] for x in self.token_api.list_revoked_tokens()]
        self.assertEqual(revoked_ids, [])

    def test_list_revoked_tokens_for_single_token(self):
        self.check_list_revoked_tokens([self.delete_token()])

    def test_list_revoked_tokens_for_multiple_tokens(self):
        self.check_list_revoked_tokens([self.delete_token()
                                        for x in xrange(2)])
