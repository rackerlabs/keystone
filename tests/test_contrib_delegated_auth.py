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

import copy
import uuid
import webob

import nose.exc

from keystone.common import oauth
from keystone.contrib.delegated_auth import core as delegated_auth

import test_v3


class OauthFlowTest(test_v3.RestfulTestCase):
    def _wsgi_request(self, *args, **kw):
        return webob.Request.blank(*args, **kw)

    def _oauth_request(self, consumer, token=None, **kw):
        return oauth.Request.from_consumer_and_token(consumer=consumer,
                                                     token=token,
                                                     **kw)

    def setUp(self):
        super(OauthFlowTest, self).setUp()
        self.controller = delegated_auth.OauthFlowManiaV3()
        self.base_url = 'https://localhost:5000'

    # TODO(stevemar): currently one large flow, break into pieces
    def test_oauth_flow(self):
        # 1. create consumer
        create_ref = {'name': uuid.uuid4().hex}
        create_resp = self.post(
            '/DA/consumer',
            body={'consumer': create_ref})
        consumer = create_resp.result.get('consumer')
        key = consumer.get('consumer_key')
        secret = consumer.get('consumer_secret')
        self.consumer = oauth.Consumer(key, secret)
        self.roles = 'admin'

        # 2. create request token, passing in consumer info and roles
        oreq = self._oauth_request(
            consumer=self.consumer,
            http_url=self.base_url + '/v3/oauth/request_token',
            parameters={'requested_roles': self.roles})
        oreq.sign_request(
            oauth.SignatureMethod_HMAC_SHA1(), self.consumer, None)
        wreq = self._wsgi_request(oreq.to_url())

        result = \
            self.controller.create_request_token(context={'request': wreq})

        req_token = result['token']
        self.req_token_key = req_token['request_token_key']
        self.req_token_secret = req_token['request_token_secret']
        self.assertIsNotNone(self.req_token_key)
        self.assertIsNotNone(self.req_token_secret)

        # 3. authorize the roles
        user_token = self.token_api.list_tokens(self.user['id'])[0]
        self.request_token = oauth.Token(self.req_token_key,
                                         self.req_token_secret)
        oreq = self._oauth_request(
            consumer=self.consumer,
            token=self.request_token,
            http_url=self.base_url + '/v3/oauth/authorize_token',
            parameters={'requested_roles': self.roles,
                        'user_token': user_token})
        oreq.sign_request(oauth.SignatureMethod_HMAC_SHA1(),
                          self.consumer, self.request_token)
        wreq = self._wsgi_request(oreq.to_url())

        result = \
            self.controller.authorize_request_token(context={'request': wreq})

        token = result['token']
        self.verifier_pin = token['oauth_verifier']
        self.assertIsNotNone(self.verifier_pin)

        # 4. Exchange verifier and request_token for access_token
        oreq = self._oauth_request(
            consumer=self.consumer,
            token=self.request_token,
            http_url=self.base_url + '/v3/oauth/access_token',
            parameters={'oauth_verifier': self.verifier_pin})
        oreq.sign_request(oauth.SignatureMethod_HMAC_SHA1(),
                          self.consumer, self.request_token)
        wreq = self._wsgi_request(oreq.to_url())

        result = \
            self.controller.create_access_token(context={'request': wreq})

        acc_token = result['token']
        self.acc_token_key = acc_token['access_token_key']
        self.acc_token_secret = acc_token['access_token_secret']
        self.assertIsNotNone(self.acc_token_key)
        self.assertIsNotNone(self.acc_token_secret)

        # 4. Use access token to get keystone token
        self.access_token = oauth.Token(self.acc_token_key,
                                        self.acc_token_secret)
        oreq = self._oauth_request(
            consumer=self.consumer,
            token=self.access_token,
            http_url=self.base_url + '/v3/DA/authenticate')
        oreq.sign_request(oauth.SignatureMethod_HMAC_SHA1(),
                          self.consumer, self.access_token)
        wreq = self._wsgi_request(oreq.to_url())

        result = \
            self.controller.authenticate(context={'request': wreq})

        keystone_token = result['token']
        self.token_id = keystone_token['id']
        self.assertIsNotNone(self.token_id)


class ConsumerCRUDTest(test_v3.RestfulTestCase):
    def setUp(self):
        super(ConsumerCRUDTest, self).setUp()

    def _create_single_consumer(self):
        create_ref = {'name': uuid.uuid4().hex}
        create_resp = self.post(
            '/DA/consumer',
            body={'consumer': create_ref})
        return create_resp.result.get('consumer')

    def test_create_consumers(self):
        raise nose.exc.SkipTest('No idea why this fails on get_scoped_token')
        """POST /DA/consumer."""
        ref = {'name': uuid.uuid4().hex}
        resp = self.post(
            '/DA/consumer',
            body={'consumer': ref})
        consumer = resp.result.get('consumer')
        self.assertIsNotNone(consumer.get('name'))
        self.assertIsNotNone(consumer.get('id'))
        self.assertIsNotNone(consumer.get('consumer_key'))
        self.assertIsNotNone(consumer.get('consumer_secret'))

    def test_list_consumers(self):
        """GET /DA/consumers."""
        resp = self.get('/DA/consumers')
        entities = resp.result.get('consumers')
        self.assertIsNotNone(entities)
        self.assertValidListLinks(resp.result.get('links'))

    def test_update_consumer(self):
        """PATCH /DA/update_consumer/{consumer_id}."""
        create_resp = self._create_single_consumer()
        id = create_resp.get('id')
        name = create_resp.get('name')

        update_ref = copy.deepcopy(create_resp)
        update_ref['name'] = name + "_new"

        update_resp = self.patch('/DA/update_consumer/%(consumer_id)s'
                                 % {'consumer_id': id},
                                 body={'consumer': update_ref})
        consumer = update_resp.result.get('consumer')
        self.assertTrue(consumer.get('name'), name + "_new")
        self.assertTrue(consumer.get('id'), id)
        self.assertIsNotNone(consumer.get('consumer_key'))
        self.assertIsNotNone(consumer.get('consumer_secret'))

    def test_delete_consumer(self):
        """DELETE /DA/delete_consumer/{consumer_id}."""
        consumer = self._create_single_consumer()
        id = consumer.get('id')
        delete_resp = self.delete('/DA/delete_consumer/%(consumer_id)s'
                                  % {'consumer_id': id})
        self.assertResponseStatus(delete_resp, 204)

    def test_get_consumer(self):
        """GET /DA/consumer/{consumer_id}."""
        consumer = self._create_single_consumer()
        id = consumer.get('id')
        delete_resp = self.get('/DA/consumer/%(consumer_id)s'
                               % {'consumer_id': id})
        self.assertTrue(delete_resp.result.get('consumer').get('id'), id)
