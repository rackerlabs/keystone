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
from keystone import test

import test_v3


class DelegatedAuthTests(test_v3.RestfulTestCase):
    def setUp(self):
        super(DelegatedAuthTests, self).setUp()
        self.controller = delegated_auth.OauthFlowManiaV3()
        self.base_url = 'https://localhost:5000'
        self.load_backends()
        self._generate_paste_config()
        self.admin_app = webtest.TestApp(
            self.loadapp('v3_delegated_auth', name='admin'))
        self.public_app = webtest.TestApp(
            self.loadapp('v3_delegated_auth', name='admin'))

    def tearDown(self):
        os.remove('v3_delegated_auth-paste.ini')

    def _wsgi_request(self, *args, **kw):
        return webob.Request.blank(*args, **kw)

    def _oauth_request(self, consumer, token=None, **kw):
        return oauth.Request.from_consumer_and_token(consumer=consumer,
                                                     token=token,
                                                     **kw)

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
        create_ref = {'name': uuid.uuid4().hex}
        create_resp = self.post(
            '/OS-OAUTH10A/consumer',
            body={'consumer': create_ref})
        return create_resp.result.get('consumer')

    def test_consumer_create(self):
        """POST /OS-OAUTH10A/consumer."""
        name = uuid.uuid4().hex
        ref = {'name': name}
        resp = self.post(
            '/OS-OAUTH10A/consumer',
            body={'consumer': ref})
        consumer = resp.result.get('consumer')
        self.assertEqual(consumer.get('name'), name)
        self.assertIsNotNone(consumer.get('id'))
        self.assertIsNotNone(consumer.get('consumer_key'))
        self.assertIsNotNone(consumer.get('consumer_secret'))

    def test_consumer_delete(self):
        """DELETE /OS-OAUTH10A/delete_consumer/{consumer_id}."""
        consumer = self._create_single_consumer()
        id = consumer.get('id')
        resp = self.delete('/OS-OAUTH10A/delete_consumer/%(consumer_id)s'
                           % {'consumer_id': id})
        self.assertResponseStatus(resp, 204)

    def test_consumer_get(self):
        """GET /OS-OAUTH10A/consumer/{consumer_id}."""
        consumer = self._create_single_consumer()
        id = consumer.get('id')
        delete_resp = self.get('/OS-OAUTH10A/consumer/%(consumer_id)s'
                               % {'consumer_id': id})
        self.assertTrue(delete_resp.result.get('consumer').get('id'), id)

    def test_consumer_list(self):
        """GET /OS-OAUTH10A/consumers."""
        resp = self.get('/OS-OAUTH10A/consumers')
        entities = resp.result.get('consumers')
        self.assertIsNotNone(entities)
        self.assertValidListLinks(resp.result.get('links'))

    def test_consumer_update(self):
        #raise nose.exc.SkipTest('No idea why this fails on get_scoped_token')
        """PATCH /OS-OAUTH10A/update_consumer/{consumer_id}."""
        create_resp = self._create_single_consumer()
        id = create_resp.get('id')
        name = create_resp.get('name')

        update_ref = copy.deepcopy(create_resp)
        update_ref['name'] = name + "_new"

        update_resp = self.patch('/OS-OAUTH10A/update_consumer/%(consumer_id)s'
                                 % {'consumer_id': id},
                                 body={'consumer': update_ref})
        consumer = update_resp.result.get('consumer')
        self.assertTrue(consumer.get('name'), name + "_new")
        self.assertTrue(consumer.get('id'), id)
        self.assertIsNotNone(consumer.get('consumer_key'))
        self.assertIsNotNone(consumer.get('consumer_secret'))

    def test_oauth_flow(self):
        """TEST OAUTH FLOW."""
        # 1. create consumer
        create_ref = {'name': uuid.uuid4().hex}
        create_resp = self.post(
            '/OS-OAUTH10A/consumer',
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

        result = self.controller.create_request_token({'request': wreq})

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
            http_url=self.base_url + '/v3/OS-OAUTH10A/authorize_token',
            parameters={'requested_roles': self.roles,
                        'user_token': user_token})
        oreq.sign_request(oauth.SignatureMethod_HMAC_SHA1(),
                          self.consumer, self.request_token)
        wreq = self._wsgi_request(oreq.to_url())

        result = self.controller.authorize_request_token({'request': wreq})

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

        result = self.controller.create_access_token({'request': wreq})

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
            http_url=self.base_url + '/v3/oauth/authenticate')
        oreq.sign_request(oauth.SignatureMethod_HMAC_SHA1(),
                          self.consumer, self.access_token)
        wreq = self._wsgi_request(oreq.to_url())

        result = self.controller.authenticate({'request': wreq})

        keystone_token = result['token']
        self.token_id = keystone_token['id']
        self.assertIsNotNone(self.token_id)
