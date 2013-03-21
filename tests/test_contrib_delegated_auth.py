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

from keystone.common import oauth
from keystone.contrib.delegated_auth import core as delegated_auth

import test_v3
import uuid
import webob
from copy import deepcopy


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

    # (stevemar) For now I will test this in one large flow;
    # in the future, I'd like to break this up as much as possible
    def test_oauth_flow(self):
        # 1. create consumer
        create_ref = {'name': uuid.uuid4().hex}
        create_resp = self.post(
            '/DA/consumer',
            body={'consumer': create_ref})
        consumer = create_resp.body.get('consumer')
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

        req_token = \
            self.controller.create_request_token(context={'request': wreq})

        self.req_token_key = req_token['key']
        self.req_token_secret = req_token['secret']
        self.assertIsNotNone(self.req_token_key)
        self.assertIsNotNone(self.req_token_secret)

        # 3. authorize the roles
        user_token = self.token_api.list_tokens(self.user['id'])[0]
        self.request_token = oauth.Token(self.req_token_key,
                                         self.req_token_secret)
        url = '/v3/oauth/authorize_token/token/'
        oreq = self._oauth_request(
            consumer=self.consumer,
            token=self.request_token,
            http_url=self.base_url + url + '%(user_token)s/roles/%(roles)s'
            % {'user_token': user_token, 'roles': self.roles})
        oreq.sign_request(oauth.SignatureMethod_HMAC_SHA1(),
                          self.consumer, self.request_token)
        wreq = self._wsgi_request(oreq.to_url())

        self.auth_return = \
            self.controller.authorize_request_token(context={'request': wreq},
                                                    token=user_token,
                                                    req_roles=self.roles)
        token = self.auth_return['token']
        self.verifier_pin = token['verifier']
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

        acc_token = \
            self.controller.create_access_token(context={'request': wreq})

        self.acc_token_key = acc_token['key']
        self.acc_token_secret = acc_token['secret']
        self.assertIsNotNone(self.acc_token_key)
        self.assertIsNotNone(self.acc_token_secret)


class ConsumerCRUDTest(test_v3.RestfulTestCase):
    def setUp(self):
        super(ConsumerCRUDTest, self).setUp()

    def _create_single_consumer(self):
        create_ref = {'name': uuid.uuid4().hex}
        create_resp = self.post(
            '/DA/consumer',
            body={'consumer': create_ref})
        return create_resp.body.get('consumer')

    def test_create_consumers(self):
        """POST /DA/consumer"""
        ref = {'name': uuid.uuid4().hex}
        resp = self.post(
            '/DA/consumer',
            body={'consumer': ref})
        consumer = resp.body.get('consumer')
        self.assertIsNotNone(consumer.get('name'))
        self.assertIsNotNone(consumer.get('id'))
        self.assertIsNotNone(consumer.get('consumer_key'))
        self.assertIsNotNone(consumer.get('consumer_secret'))

    def test_list_consumers(self):
        """GET /DA/consumers"""
        resp = self.get('/DA/consumers')
        entities = resp.body.get('consumers')
        self.assertIsNotNone(entities)
        self.assertValidListLinks(resp.body.get('links'))

    def test_update_consumer(self):
        """PATCH /DA/update_consumer/{consumer_id}"""
        create_resp = self._create_single_consumer()
        id = create_resp.get('id')
        name = create_resp.get('name')
        key = create_resp.get('consumer_key')
        secret = create_resp.get('consumer_secret')

        update_ref = deepcopy(create_resp)
        update_ref['name'] = name + "_new"
        update_ref['consumer_key'] = key + "_new"
        update_ref['consumer_secret'] = secret + "_new"

        update_resp = self.patch('/DA/update_consumer/%(consumer_id)s'
                                 % {'consumer_id': id},
                                 body={'consumer': update_ref})
        consumer = update_resp.body.get('consumer')
        self.assertIsNotNone(consumer.get('name'))
        self.assertIsNotNone(consumer.get('id'))
        self.assertIsNotNone(consumer.get('consumer_key'))
        self.assertIsNotNone(consumer.get('consumer_secret'))

    def test_delete_consumer(self):
        """DELETE /DA/delete_consumer/{consumer_id}"""
        consumer = self._create_single_consumer()
        id = consumer.get('id')
        delete_resp = self.delete('/DA/delete_consumer/%(consumer_id)s'
                                  % {'consumer_id': id})
        self.assertResponseStatus(delete_resp, 204)

    def test_get_consumer(self):
        """GET /DA/consumer/{consumer_id}"""
        consumer = self._create_single_consumer()
        id = consumer.get('id')
        delete_resp = self.get('/DA/consumer/%(consumer_id)s'
                               % {'consumer_id': id})
        self.assertTrue(delete_resp.body.get('consumer').get('id'), id)
