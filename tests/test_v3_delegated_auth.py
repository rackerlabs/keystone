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
import os
import uuid
import webob
import webtest

from keystone.common import oauth
from keystone.contrib.delegated_auth import core as delegated_auth
from keystone import exception
from keystone import test

import test_v3


class DelegatedAuthTests(test_v3.RestfulTestCase):
    def setUp(self):
        super(DelegatedAuthTests, self).setUp()
        self.controller = delegated_auth.OauthFlowManiaV3()
        self.base_url = 'https://localhost:5000'
        self.roles = 'admin'
        self.load_backends()
        self._generate_paste_config()
        self.admin_app = webtest.TestApp(
            self.loadapp('v3_delegated_auth', name='admin'))
        self.public_app = webtest.TestApp(
            self.loadapp('v3_delegated_auth', name='admin'))

    def tearDown(self):
        os.remove('v3_delegated_auth-paste.ini')

    def _generate_paste_config(self):
        # Generate a file, based on keystone-paste.ini,
        # that includes oauth_extension in the pipeline
        old_pipeline = " ec2_extension "
        new_pipeline = " oauth_extension ec2_extension "

        with open(test.etcdir('keystone-paste.ini'), 'r') as f:
            contents = f.read()
        new_contents = contents.replace(old_pipeline, new_pipeline)
        with open('v3_delegated_auth-paste.ini', 'w') as f:
            f.write(new_contents)

    def _create_single_consumer(self):
        ref = {'name': uuid.uuid4().hex}
        resp = self.post(
            '/OS-OAUTH10A/consumer',
            body={'consumer': ref})
        return resp.result.get('consumer')

    def test_consumer_create(self):
        """POST /OS-OAUTH10A/consumer."""
        name = uuid.uuid4().hex
        ref = {'name': name}
        resp = self.post(
            '/OS-OAUTH10A/consumer',
            body={'consumer': ref})
        consumer = resp.result.get('consumer')
        consumer_id = consumer.get('id')
        key = consumer.get('consumer_key')
        self.assertEqual(consumer.get('name'), name)
        self.assertIsNotNone(consumer_id)
        self.assertIsNotNone(key)
        self.assertEqual(consumer_id, key)
        self.assertIsNotNone(consumer.get('consumer_secret'))

    def test_consumer_delete(self):
        """DELETE /OS-OAUTH10A/delete_consumer/{consumer_id}."""
        consumer = self._create_single_consumer()
        consumer_id = consumer.get('id')
        resp = self.delete('/OS-OAUTH10A/delete_consumer/%(consumer_id)s'
                           % {'consumer_id': consumer_id})
        self.assertResponseStatus(resp, 204)

    def test_consumer_get(self):
        """GET /OS-OAUTH10A/consumer/{consumer_id}."""
        consumer = self._create_single_consumer()
        consumer_id = consumer.get('id')
        resp = self.get('/OS-OAUTH10A/consumer/%(consumer_id)s'
                        % {'consumer_id': consumer_id})
        self.assertTrue(resp.result.get('consumer').get('id'), consumer_id)

    def test_consumer_list(self):
        """GET /OS-OAUTH10A/consumers."""
        resp = self.get('/OS-OAUTH10A/consumers')
        entities = resp.result.get('consumers')
        self.assertIsNotNone(entities)
        self.assertValidListLinks(resp.result.get('links'))

    def test_consumer_update(self):
        """PATCH /OS-OAUTH10A/update_consumer/{consumer_id}."""
        consumer = self._create_single_consumer()
        original_id = consumer.get('id')
        original_name = consumer.get('name')
        original_key = consumer.get('consumer_key')
        original_secret = consumer.get('consumer_secret')
        update_name = original_name + "_new"

        update_ref = copy.deepcopy(consumer)
        update_ref['name'] = update_name

        update_resp = self.patch('/OS-OAUTH10A/update_consumer/%(consumer_id)s'
                                 % {'consumer_id': original_id},
                                 body={'consumer': update_ref})
        consumer = update_resp.result.get('consumer')
        self.assertEqual(consumer.get('name'), update_name)
        self.assertEqual(consumer.get('id'), original_id)
        self.assertEqual(consumer.get('consumer_key'), original_key)
        self.assertEqual(consumer.get('consumer_secret'), original_secret)

    def _wsgi_request(self, *args, **kw):
        return webob.Request.blank(*args, **kw)

    def _oauth_request(self, consumer, token=None, **kw):
        return oauth.Request.from_consumer_and_token(consumer=consumer,
                                                     token=token,
                                                     **kw)

    def _wreq_create_request_token(self, consumer, roles):
        oreq = self._oauth_request(
            consumer=consumer,
            http_url=self.base_url + '/v3/oauth/request_token',
            http_method='GET',
            parameters={'requested_roles': self.roles})
        hmac = oauth.SignatureMethod_HMAC_SHA1()
        oreq.sign_request(hmac, consumer, None)
        return self._wsgi_request(oreq.to_url())

    def _wreq_authorize_request_token(self, consumer, request_token,
                                      roles, user_token):
        oreq = self._oauth_request(
            consumer=consumer, token=request_token,
            http_url=self.base_url + '/v3/oauth/authorize',
            http_method='POST',
            parameters={'requested_roles': roles, 'user_token': user_token})
        hmac = oauth.SignatureMethod_HMAC_SHA1()
        oreq.sign_request(hmac, consumer, request_token)
        return self._wsgi_request(oreq.to_url())

    def _wreq_create_access_token(self, consumer, token):
        oreq = self._oauth_request(
            consumer=consumer, token=token,
            http_method='POST',
            http_url=self.base_url + '/v3/oauth/access_token')
        hmac = oauth.SignatureMethod_HMAC_SHA1()
        oreq.sign_request(hmac, consumer, token)
        return self._wsgi_request(oreq.to_url())

    def _wreq_authenticate_access_token(self, consumer, token):
        oreq = self._oauth_request(
            consumer=consumer, token=token,
            http_method='POST',
            http_url=self.base_url + '/v3/oauth/authenticate')
        hmac = oauth.SignatureMethod_HMAC_SHA1()
        oreq.sign_request(hmac, consumer, token)
        return self._wsgi_request(oreq.to_url())

    def test_correct_oauth_flow(self):
        """TEST CORRECT OAUTH FLOW."""
        # 1. create consumer
        consumer = self._create_single_consumer()
        consumer_key = consumer.get('consumer_key')
        consumer_secret = consumer.get('consumer_secret')
        consumer = oauth.Consumer(consumer_key, consumer_secret)

        # 2. create request token
        wreq = self._wreq_create_request_token(consumer, self.roles)
        result = self.controller.create_request_token({'request': wreq})
        request_key = result['token']['request_token_key']
        request_secret = result['token']['request_token_secret']
        request_token = oauth.Token(request_key, request_secret)

        # 3. authorize request token
        user_token = self.token_api.list_tokens(self.user['id'])[0]
        wreq = self._wreq_authorize_request_token(consumer, request_token,
                                                  self.roles, user_token)
        result = self.controller.authorize({'request': wreq})
        verifier = result['token']['oauth_verifier']
        self.assertIsNotNone(verifier)

        # 4. create access token
        request_token.set_verifier(verifier)
        wreq = self._wreq_create_access_token(consumer, request_token)
        result = self.controller.create_access_token({'request': wreq})
        access_key = result['token']['access_token_key']
        access_secret = result['token']['access_token_secret']
        access_token = oauth.Token(access_key, access_secret)

        # 5. authenticate access token
        wreq = self._wreq_authenticate_access_token(consumer, access_token)
        result = self.controller.authenticate({'request': wreq})
        keystone_token_id = result['token']['id']
        self.assertIsNotNone(keystone_token_id)

    def test_request_token_fails_wrong_consumer_secret(self):
        consumer = self._create_single_consumer()
        consumer_key = consumer.get('consumer_key')
        consumer = oauth.Consumer(consumer_key, "bad_secret")
        wreq = self._wreq_create_request_token(consumer, self.roles)
        self.assertRaises(RuntimeError,
                          self.controller.create_request_token,
                          {'request': wreq})

    def test_authorize_req_token_fails_wrong_req_token_secret(self):
        consumer = self._create_single_consumer()
        consumer_key = consumer.get('consumer_key')
        consumer_secret = consumer.get('consumer_secret')
        consumer = oauth.Consumer(consumer_key, consumer_secret)

        wreq = self._wreq_create_request_token(consumer, self.roles)
        result = self.controller.create_request_token({'request': wreq})
        request_key = result['token']['request_token_key']
        request_token = oauth.Token(request_key, "bad_secret")

        user_token = self.token_api.list_tokens(self.user['id'])[0]
        wreq = self._wreq_authorize_request_token(consumer, request_token,
                                                  self.roles, user_token)
        self.assertRaises(RuntimeError,
                          self.controller.authorize,
                          {'request': wreq})

    def test_get_access_token_fails_wrong_verifier(self):
        consumer = self._create_single_consumer()
        consumer_key = consumer.get('consumer_key')
        consumer_secret = consumer.get('consumer_secret')
        consumer = oauth.Consumer(consumer_key, consumer_secret)

        wreq = self._wreq_create_request_token(consumer, self.roles)
        result = self.controller.create_request_token({'request': wreq})
        request_key = result['token']['request_token_key']
        request_secret = result['token']['request_token_secret']
        request_token = oauth.Token(request_key, request_secret)

        user_token = self.token_api.list_tokens(self.user['id'])[0]
        wreq = self._wreq_authorize_request_token(consumer, request_token,
                                                  self.roles, user_token)
        result = self.controller.authorize({'request': wreq})

        request_token.set_verifier("bad verifier")
        wreq = self._wreq_create_access_token(consumer, request_token)
        self.assertRaises(exception.Unauthorized,
                          self.controller.create_access_token,
                          {'request': wreq})

    def test_authenticate_fails_wrong_access_token_secret(self):
        consumer = self._create_single_consumer()
        consumer_key = consumer.get('consumer_key')
        consumer_secret = consumer.get('consumer_secret')
        consumer = oauth.Consumer(consumer_key, consumer_secret)

        wreq = self._wreq_create_request_token(consumer, self.roles)
        result = self.controller.create_request_token({'request': wreq})
        request_key = result['token']['request_token_key']
        request_secret = result['token']['request_token_secret']
        request_token = oauth.Token(request_key, request_secret)

        user_token = self.token_api.list_tokens(self.user['id'])[0]
        wreq = self._wreq_authorize_request_token(consumer, request_token,
                                                  self.roles, user_token)
        result = self.controller.authorize({'request': wreq})
        verifier = result['token']['oauth_verifier']
        self.assertIsNotNone(verifier)

        request_token.set_verifier(verifier)
        wreq = self._wreq_create_access_token(consumer, request_token)
        result = self.controller.create_access_token({'request': wreq})
        access_key = result['token']['access_token_key']
        access_token = oauth.Token(access_key, "bad_secret")

        wreq = self._wreq_authenticate_access_token(consumer, access_token)
        self.assertRaises(RuntimeError,
                          self.controller.authenticate,
                          {'request': wreq})
