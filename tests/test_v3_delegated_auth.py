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

DA_PASTE_FILE = 'v3_delegated_auth-paste.ini'


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
        self.identity_api.delete_role(self.role_id)
        os.remove(DA_PASTE_FILE)

    def _generate_paste_config(self):
        # Generate a file, based on keystone-paste.ini,
        # that includes oauth_extension in the pipeline
        old_pipeline = " ec2_extension "
        new_pipeline = " oauth_extension ec2_extension "

        with open(test.etcdir('keystone-paste.ini'), 'r') as f:
            contents = f.read()
        new_contents = contents.replace(old_pipeline, new_pipeline)
        with open(DA_PASTE_FILE, 'w') as f:
            f.write(new_contents)

    def _create_single_consumer(self):
        ref = {'name': uuid.uuid4().hex}
        resp = self.post(
            '/OS-OAUTH10A/consumers',
            body={'consumer': ref})
        return resp.result.get('consumer')

    def _wsgi_request(self, *args, **kw):
        return webob.Request.blank(*args, **kw)

    def _oauth_request(self, consumer, token=None, **kw):
        return oauth.Request.from_consumer_and_token(consumer=consumer,
                                                     token=token,
                                                     **kw)

    def _wreq_create_request_token(self, consumer, roles):
        oreq = self._oauth_request(
            consumer=consumer,
            http_url=self.base_url + '/v3/OS-OAUTH10A/request_token',
            http_method='GET',
            parameters={'requested_roles': roles})
        hmac = oauth.SignatureMethod_HMAC_SHA1()
        oreq.sign_request(hmac, consumer, None)
        return self._wsgi_request(oreq.to_url())

    def _wreq_create_access_token(self, consumer, token):
        oreq = self._oauth_request(
            consumer=consumer, token=token,
            http_method='GET',
            http_url=self.base_url + '/v3/OS-OAUTH10A/access_token')
        hmac = oauth.SignatureMethod_HMAC_SHA1()
        oreq.sign_request(hmac, consumer, token)
        return self._wsgi_request(oreq.to_url())

    def _wreq_authenticate_access_token(self, consumer, token):
        oreq = self._oauth_request(
            consumer=consumer, token=token,
            http_method='GET',
            http_url=self.base_url + '/v3/OS-OAUTH10A/authenticate')
        hmac = oauth.SignatureMethod_HMAC_SHA1()
        oreq.sign_request(hmac, consumer, token)
        return self._wsgi_request(oreq.to_url())

    def _authorize_request_token(self, request_key, roles):
        resp = self.post('/OS-OAUTH10A/authorize/%s/%s' % (request_key, roles))
        return resp


class ConsumerTests(DelegatedAuthTests):

    def test_consumer_create(self):
        name = uuid.uuid4().hex
        ref = {'name': name}
        resp = self.post(
            '/OS-OAUTH10A/consumers',
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
        consumer = self._create_single_consumer()
        consumer_id = consumer.get('id')
        resp = self.delete('/OS-OAUTH10A/consumers/%(consumer_id)s'
                           % {'consumer_id': consumer_id})
        self.assertResponseStatus(resp, 204)

    def test_consumer_get(self):
        consumer = self._create_single_consumer()
        consumer_id = consumer.get('id')
        resp = self.get('/OS-OAUTH10A/consumers/%(consumer_id)s'
                        % {'consumer_id': consumer_id})
        self.assertTrue(resp.result.get('consumer').get('id'), consumer_id)

    def test_consumer_list(self):
        resp = self.get('/OS-OAUTH10A/consumers')
        entities = resp.result.get('consumers')
        self.assertIsNotNone(entities)
        self.assertValidListLinks(resp.result.get('links'))

    def test_consumer_update(self):
        consumer = self._create_single_consumer()
        original_id = consumer.get('id')
        original_name = consumer.get('name')
        original_key = consumer.get('consumer_key')
        original_secret = consumer.get('consumer_secret')
        update_name = original_name + "_new"

        update_ref = copy.deepcopy(consumer)
        update_ref['name'] = update_name
        update_resp = self.patch('/OS-OAUTH10A/consumers/%(consumer_id)s'
                                 % {'consumer_id': original_id},
                                 body={'consumer': update_ref})
        consumer = update_resp.result.get('consumer')
        self.assertEqual(consumer.get('name'), update_name)
        self.assertEqual(consumer.get('id'), original_id)
        self.assertEqual(consumer.get('consumer_key'), original_key)
        self.assertEqual(consumer.get('consumer_secret'), original_secret)

    def test_consumer_update_bad_params(self):
        consumer = self._create_single_consumer()
        original_id = consumer.get('id')
        original_name = consumer.get('name')
        update_name = original_name + "_new"

        update_ref = copy.deepcopy(consumer)
        update_ref['name'] = update_name
        update_ref['consumer_key'] = update_name
        update_ref['consumer_secret'] = update_name
        update_ref['id'] = update_name
        self.patch('/OS-OAUTH10A/consumers/%(consumer_id)s'
                   % {'consumer_id': original_id},
                   body={'consumer': update_ref},
                   expected_status=400)


class OAuthFlowTests(DelegatedAuthTests):

    def test_oauth_flow(self):
        consumer = self._create_single_consumer()
        consumer_key = consumer.get('consumer_key')
        consumer_secret = consumer.get('consumer_secret')
        self.consumer = oauth.Consumer(consumer_key, consumer_secret)
        self.assertIsNotNone(self.consumer.key)

        wreq = self._wreq_create_request_token(self.consumer, self.roles)
        result = self.controller.create_request_token({'request': wreq})
        request_key = result['token']['request_token_key']
        request_secret = result['token']['request_token_secret']
        self.request_token = oauth.Token(request_key, request_secret)
        self.assertIsNotNone(self.request_token.key)

        resp = self._authorize_request_token(self.request_token.key,
                                             self.roles)
        self.verifier = resp.result['token']['oauth_verifier']

        self.request_token.set_verifier(self.verifier)
        wreq = self._wreq_create_access_token(self.consumer,
                                              self.request_token)
        result = self.controller.create_access_token({'request': wreq})
        access_key = result['token']['access_token_key']
        access_secret = result['token']['access_token_secret']
        self.access_token = oauth.Token(access_key, access_secret)
        self.assertIsNotNone(self.access_token.key)

        wreq = self._wreq_authenticate_access_token(self.consumer,
                                                    self.access_token)
        result = self.controller.authenticate({'request': wreq})
        self.keystone_token = result['token']
        self.keystone_token_id = result['token']['id']
        self.assertIsNotNone(self.keystone_token_id)


class AdminTasks(OAuthFlowTests):
    def test_list_and_delete_authorizations(self):
        self.test_oauth_flow()
        # List Authorizations should be > 0
        resp = self.get('/OS-OAUTH10A/user/%(user_id)s/authorizations'
                        % {'user_id': self.user_id})
        entities = resp.result.get('authorizations')
        self.assertIsNotNone(entities)
        self.assertValidListLinks(resp.result.get('links'))

        # Delete Authorization
        resp = self.delete('/OS-OAUTH10A/user/%(user)s/authorization/%(auth)s'
                           % {'user': self.user_id,
                              'auth': self.access_token.key})
        self.assertResponseStatus(resp, 204)

        # List Authorization should be 0
        resp = self.get('/OS-OAUTH10A/user/%(user_id)s/authorizations'
                        % {'user_id': self.user_id})
        entities = resp.result.get('authorizations')
        self.assertIsNotNone(entities)
        self.assertValidListLinks(resp.result.get('links'))


class OAuthTokenTests(OAuthFlowTests):

    def test_keystone_token_is_valid(self):
        self.test_oauth_flow()
        headers = {'X-Subject-Token': self.keystone_token_id,
                   'X-Auth-Token': self.keystone_token_id}
        r = self.get('/auth/tokens', headers=headers)
        self.assertValidTokenResponse(r, self.user)

        # now verify the oauth section
        oauth_section = r.result['token']['OS-OAUTH10A:oauth']
        self.assertEquals(oauth_section['access_token_key'],
                          self.access_token.key)
        self.assertEquals(oauth_section['consumer_id'], self.consumer.key)

    def test_delete_authorization_also_revokes_token(self):
        self.test_oauth_flow()

        # Delete access token
        resp = self.delete('/OS-OAUTH10A/user/%(user)s/authorization/%(auth)s'
                           % {'user': self.user_id,
                              'auth': self.access_token.key})
        self.assertResponseStatus(resp, 204)

        # Check Keystone Token no longer exists
        headers = {'X-Subject-Token': self.keystone_token_id,
                   'X-Auth-Token': self.keystone_token_id}
        self.head('/auth/tokens', headers=headers,
                  expected_status=401)

    def test_deleting_consumer_also_deletes_tokens(self):
        self.test_oauth_flow()

        # Delete consumer
        consumer_id = self.consumer.key
        resp = self.delete('/OS-OAUTH10A/consumers/%(consumer_id)s'
                           % {'consumer_id': consumer_id})
        self.assertResponseStatus(resp, 204)

        # List Authorization should be 0
        resp = self.get('/OS-OAUTH10A/user/%(user_id)s/authorizations'
                        % {'user_id': self.user_id})
        entities = resp.result.get('authorizations')
        self.assertEqual(len(entities), 0)

        # Check Keystone Token no longer exists
        headers = {'X-Subject-Token': self.keystone_token_id,
                   'X-Auth-Token': self.keystone_token_id}
        self.head('/auth/tokens', headers=headers,
                  expected_status=401)

    def test_change_user_password_also_deletes_tokens(self):
        self.skipTest('Not sure why last call is not being caught')
        self.test_oauth_flow()

        # delegated keystone token exists
        headers = {'X-Subject-Token': self.keystone_token_id,
                   'X-Auth-Token': self.keystone_token_id}
        r = self.get('/auth/tokens', headers=headers)
        self.assertValidTokenResponse(r, self.user)

        user = {'password': uuid.uuid4().hex}
        r = self.patch('/users/%(user_id)s' % {
            'user_id': self.user['id']},
            body={'user': user})

        headers = {'X-Subject-Token': self.keystone_token_id,
                   'X-Auth-Token': self.keystone_token_id}
        self.head('/auth/tokens', headers=headers,
                  expected_status=401)

    def test_deleting_project_also_deletes_tokens(self):
        pass

    def test_deleting_role_also_deletes_tokens(self):
        pass

    def test_token_chaining_is_not_allowed(self):
        self.test_oauth_flow()

        #attempt to re-authenticate (token chain) with the given token
        path = '/v3/auth/tokens/'
        auth_data = self.build_authentication_request(
            token=self.keystone_token_id)

        self.admin_request(
            path=path,
            body=auth_data,
            token=self.keystone_token_id,
            method='POST',
            expected_status=403)


class MaliciousOAuthTests(DelegatedAuthTests):

    def test_bad_consumer_secret(self):
        consumer = self._create_single_consumer()
        consumer_key = consumer.get('consumer_key')
        consumer = oauth.Consumer(consumer_key, "bad_secret")
        wreq = self._wreq_create_request_token(consumer, self.roles)
        self.assertRaises(RuntimeError,
                          self.controller.create_request_token,
                          {'request': wreq})

    def test_bad_request_token_key(self):
        consumer = self._create_single_consumer()
        consumer_key = consumer.get('consumer_key')
        consumer_secret = consumer.get('consumer_secret')
        consumer = oauth.Consumer(consumer_key, consumer_secret)
        wreq = self._wreq_create_request_token(consumer, self.roles)
        self.controller.create_request_token({'request': wreq})
        path = '/v3/OS-OAUTH10A/authorize/%s/%s' % ("bad_key", self.roles)
        self.admin_request(
            path=path, token='ADMIN', method='PUT', expected_status=404)

    def test_bad_verifier(self):
        consumer = self._create_single_consumer()
        consumer_key = consumer.get('consumer_key')
        consumer_secret = consumer.get('consumer_secret')
        consumer = oauth.Consumer(consumer_key, consumer_secret)

        wreq = self._wreq_create_request_token(consumer, self.roles)
        result = self.controller.create_request_token({'request': wreq})
        request_key = result['token']['request_token_key']
        request_secret = result['token']['request_token_secret']
        request_token = oauth.Token(request_key, request_secret)

        resp = self._authorize_request_token(request_key, self.roles)
        verifier = resp.result['token']['oauth_verifier']
        self.assertIsNotNone(verifier)

        request_token.set_verifier("bad verifier")
        wreq = self._wreq_create_access_token(consumer, request_token)
        self.assertRaises(exception.Unauthorized,
                          self.controller.create_access_token,
                          {'request': wreq})

    def test_bad_access_token_secret(self):
        consumer = self._create_single_consumer()
        consumer_key = consumer.get('consumer_key')
        consumer_secret = consumer.get('consumer_secret')
        consumer = oauth.Consumer(consumer_key, consumer_secret)

        wreq = self._wreq_create_request_token(consumer, self.roles)
        result = self.controller.create_request_token({'request': wreq})
        request_key = result['token']['request_token_key']
        request_secret = result['token']['request_token_secret']
        request_token = oauth.Token(request_key, request_secret)

        resp = self._authorize_request_token(request_key, self.roles)
        verifier = resp.result['token']['oauth_verifier']
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

    def test_bad_requested_roles(self):
        consumer = self._create_single_consumer()
        consumer_key = consumer.get('consumer_key')
        consumer_secret = consumer.get('consumer_secret')
        consumer = oauth.Consumer(consumer_key, consumer_secret)

        wreq = self._wreq_create_request_token(consumer, "bad_role")
        self.assertRaises(exception.Unauthorized,
                          self.controller.create_request_token,
                          {'request': wreq})

    def test_bad_authorizing_roles(self):
        consumer = self._create_single_consumer()
        consumer_key = consumer.get('consumer_key')
        consumer_secret = consumer.get('consumer_secret')
        consumer = oauth.Consumer(consumer_key, consumer_secret)

        wreq = self._wreq_create_request_token(consumer, self.roles)
        result = self.controller.create_request_token({'request': wreq})
        request_key = result['token']['request_token_key']

        self.identity_api.remove_role_from_user_and_project(self.user_id,
                                                            self.project_id,
                                                            self.role_id)
        path = '/v3/OS-OAUTH10A/authorize/%s/%s' % (request_key, self.roles)
        self.admin_request(
            path=path, token='ADMIN', method='POST', expected_status=404)

    def test_expired_request_token(self):
        pass

    def test_expired_access_token(self):
        pass
