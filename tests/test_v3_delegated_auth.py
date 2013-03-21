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
import json
import os
import test_v3
import urlparse
import uuid
import webob
import webtest

from keystone.common import oauth
from keystone import config
from keystone.contrib.delegated_auth import core as delegated_auth
from keystone import exception
from keystone import test


DA_PASTE_FILE = 'v3_delegated_auth-paste.ini'
CONF = config.CONF


class DelegatedAuthTests(test_v3.RestfulTestCase):
    def setUp(self):
        super(DelegatedAuthTests, self).setUp()
        self.controller = delegated_auth.OAuthControllerV3()
        self.base_url = 'http://localhost:5000'
        self.load_backends()
        self._generate_paste_config()
        self.admin_app = webtest.TestApp(
            self.loadapp('v3_delegated_auth', name='admin'))
        self.public_app = webtest.TestApp(
            self.loadapp('v3_delegated_auth', name='admin'))

    def tearDown(self):
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
        ref = {'description': uuid.uuid4().hex}
        resp = self.post(
            '/OS-OAUTH1/consumers',
            body={'consumer': ref})
        return resp.result.get('consumer')

    def _wsgi_request(self, *args, **kw):
        return webob.Request.blank(*args, **kw)

    def _oauth_request(self, consumer, token=None, **kw):
        return oauth.Request.from_consumer_and_token(consumer=consumer,
                                                     token=token,
                                                     **kw)

    def _wreq_create_request_token(self, consumer, role, project_id):
        oreq = self._oauth_request(
            consumer=consumer,
            http_url=self.base_url + '/v3/OS-OAUTH1/request_token',
            http_method='GET',
            parameters={'requested_role_ids': role,
                        'requested_project_id': project_id})
        hmac = oauth.SignatureMethod_HMAC_SHA1()
        oreq.sign_request(hmac, consumer, None)
        return self._wsgi_request(oreq.to_url())

    def _wreq_create_access_token(self, consumer, token):
        oreq = self._oauth_request(
            consumer=consumer, token=token,
            http_method='GET',
            http_url=self.base_url + '/v3/OS-OAUTH1/access_token')
        hmac = oauth.SignatureMethod_HMAC_SHA1()
        oreq.sign_request(hmac, consumer, token)
        return self._wsgi_request(oreq.to_url())

    def _authenticate_access_token(self, consumer, token):
        headers = {'Content-Type': 'application/json'}
        body = {'auth': {'identity': {'methods': [], 'oauth':
                                     {'access_token_id': {}}},
                         'scope': {'project': {'id': {}}}
                         }
                }
        body['auth']['identity']['methods'].append('oauth')
        body['auth']['identity']['oauth']['access_token_id'] = token.key
        body['auth']['scope']['project']['id'] = self.project_id

        # this is kind of a hack
        url = 'http://localhost:80/auth/tokens'
        oreq = self._oauth_request(
            consumer=consumer, token=token,
            http_method='POST',
            http_url=url)
        hmac = oauth.SignatureMethod_HMAC_SHA1()
        oreq.sign_request(hmac, consumer, token)
        headers.update(oreq.to_header())
        r = self.admin_request(
            method='POST',
            headers=headers,
            path='/v3/auth/tokens',
            body=body)
        token_id = r.headers.get('X-Subject-Token')
        content_dict = json.loads(r.body)
        token = content_dict.get('token')
        return token_id, token

    def _authorize_request_token(self, request_id):
        return '/OS-OAUTH1/authorize/%s' % (request_id)


class ConsumerCRUDTests(DelegatedAuthTests):

    def test_consumer_create(self):
        description = uuid.uuid4().hex
        ref = {'description': description}
        resp = self.post(
            '/OS-OAUTH1/consumers',
            body={'consumer': ref})
        consumer = resp.result.get('consumer')
        consumer_id = consumer.get('id')
        self.assertEqual(consumer.get('description'), description)
        self.assertIsNotNone(consumer_id)
        self.assertIsNotNone(consumer.get('consumer_secret'))

    def test_consumer_delete(self):
        consumer = self._create_single_consumer()
        consumer_id = consumer.get('id')
        resp = self.delete('/OS-OAUTH1/consumers/%(consumer_id)s'
                           % {'consumer_id': consumer_id})
        self.assertResponseStatus(resp, 204)

    def test_consumer_get(self):
        consumer = self._create_single_consumer()
        consumer_id = consumer.get('id')
        resp = self.get('/OS-OAUTH1/consumers/%(consumer_id)s'
                        % {'consumer_id': consumer_id})
        self.assertTrue(resp.result.get('consumer').get('id'), consumer_id)

    def test_consumer_list(self):
        resp = self.get('/OS-OAUTH1/consumers')
        entities = resp.result.get('consumers')
        self.assertIsNotNone(entities)
        self.assertValidListLinks(resp.result.get('links'))

    def test_consumer_update(self):
        consumer = self._create_single_consumer()
        original_id = consumer.get('id')
        original_description = consumer.get('description')
        original_secret = consumer.get('consumer_secret')
        update_description = original_description + "_new"

        update_ref = {'description': update_description}
        update_resp = self.patch('/OS-OAUTH1/consumers/%(consumer_id)s'
                                 % {'consumer_id': original_id},
                                 body={'consumer': update_ref})
        consumer = update_resp.result.get('consumer')
        self.assertEqual(consumer.get('description'), update_description)
        self.assertEqual(consumer.get('id'), original_id)
        self.assertEqual(consumer.get('consumer_secret'), original_secret)

    def test_consumer_update_bad_secret(self):
        consumer = self._create_single_consumer()
        original_id = consumer.get('id')
        update_ref = copy.deepcopy(consumer)
        update_ref['description'] = uuid.uuid4().hex
        update_ref['consumer_secret'] = uuid.uuid4().hex
        self.patch('/OS-OAUTH1/consumers/%(consumer_id)s'
                   % {'consumer_id': original_id},
                   body={'consumer': update_ref},
                   expected_status=400)

    def test_consumer_update_bad_id(self):
        consumer = self._create_single_consumer()
        original_id = consumer.get('id')
        original_description = consumer.get('description')
        update_description = original_description + "_new"

        update_ref = copy.deepcopy(consumer)
        update_ref['description'] = update_description
        update_ref['id'] = update_description
        self.patch('/OS-OAUTH1/consumers/%(consumer_id)s'
                   % {'consumer_id': original_id},
                   body={'consumer': update_ref},
                   expected_status=400)

    def test_consumer_create_no_description(self):
        resp = self.post('/OS-OAUTH1/consumers', body={'consumer': {}})
        consumer = resp.result.get('consumer')
        consumer_id = consumer.get('id')
        self.assertEqual(consumer.get('description'), None)
        self.assertIsNotNone(consumer_id)
        self.assertIsNotNone(consumer.get('consumer_secret'))

    def test_consumer_get_bad_id(self):
        self.get('/OS-OAUTH1/consumers/%(consumer_id)s'
                 % {'consumer_id': uuid.uuid4().hex},
                 expected_status=404)


class OAuthFlowTests(DelegatedAuthTests):

    def test_oauth_flow(self):
        consumer = self._create_single_consumer()
        consumer_id = consumer.get('id')
        consumer_secret = consumer.get('consumer_secret')
        self.consumer = oauth.Consumer(consumer_id, consumer_secret)
        self.assertIsNotNone(self.consumer.key)

        wreq = self._wreq_create_request_token(self.consumer,
                                               self.role_id,
                                               self.project_id)
        result = self.controller.create_request_token({'request': wreq})
        credentials = urlparse.parse_qs(result)
        request_key = credentials.get('oauth_token')[0]
        request_secret = credentials.get('oauth_token_secret')[0]
        self.request_token = oauth.Token(request_key, request_secret)
        self.assertIsNotNone(self.request_token.key)

        url = self._authorize_request_token(request_key)
        resp = self.put(url, expected_status=200)
        self.verifier = resp.result['token']['oauth_verifier']

        self.request_token.set_verifier(self.verifier)
        wreq = self._wreq_create_access_token(self.consumer,
                                              self.request_token)
        result = self.controller.create_access_token({'request': wreq})
        credentials = urlparse.parse_qs(result)
        access_key = credentials.get('oauth_token')[0]
        access_secret = credentials.get('oauth_token_secret')[0]
        self.access_token = oauth.Token(access_key, access_secret)
        self.assertIsNotNone(self.access_token.key)

        token_id, token = self._authenticate_access_token(self.consumer,
                                                          self.access_token)
        self.keystone_token = token
        self.keystone_token_id = token_id
        self.assertIsNotNone(self.keystone_token_id)


class AccessTokenCRUDTests(OAuthFlowTests):
    def test_delete_access_token_dne(self):
        self.delete('/users/%(user)s/OS-OAUTH1/access_tokens/%(auth)s'
                    % {'user': self.user_id,
                       'auth': uuid.uuid4().hex},
                    expected_status=404)

    def test_list_no_access_tokens(self):
        resp = self.get('/users/%(user_id)s/OS-OAUTH1/access_tokens'
                        % {'user_id': self.user_id})
        entities = resp.result.get('access_tokens')
        self.assertTrue(len(entities) == 0)
        self.assertValidListLinks(resp.result.get('links'))

    def test_get_access_token(self):
        self.test_oauth_flow()
        resp = self.get('/users/%s/OS-OAUTH1/access_tokens/%s'
                        % (self.user_id, self.access_token.key))
        entity = resp.result.get('access_token')
        self.assertTrue(entity['id'], self.access_token.key)
        self.assertTrue(entity['consumer_id'], self.consumer.key)

    def test_get_access_token_dne(self):
        self.get('/users/%s/OS-OAUTH1/access_tokens/%s'
                 % (self.user_id, uuid.uuid4().hex),
                 expected_status=404)

    def test_list_all_roles_in_access_token(self):
        self.test_oauth_flow()
        resp = self.get('/users/%s/OS-OAUTH1/access_tokens/%s/roles'
                        % (self.user_id, self.access_token.key))
        entities = resp.result.get('roles')
        self.assertTrue(len(entities) > 0)
        self.assertValidListLinks(resp.result.get('links'))

    def test_get_role_in_access_token(self):
        self.test_oauth_flow()
        url = '/users/%s/OS-OAUTH1/access_tokens/%s/roles/%s'
        resp = self.get(url % (self.user_id,
                               self.access_token.key,
                               self.role_id))
        entity = resp.result.get('role')
        self.assertTrue(entity['id'], self.role_id)

    def test_get_role_in_access_token_dne(self):
        self.test_oauth_flow()
        url = '/users/%s/OS-OAUTH1/access_tokens/%s/roles/%s'
        self.get(url % (self.user_id,
                        self.access_token.key,
                        uuid.uuid4().hex),
                 expected_status=404)

    def test_list_and_delete_access_tokens(self):
        self.test_oauth_flow()
        # List access_tokens should be > 0
        resp = self.get('/users/%(user_id)s/OS-OAUTH1/access_tokens'
                        % {'user_id': self.user_id})
        entities = resp.result.get('access_tokens')
        self.assertTrue(len(entities) > 0)
        self.assertValidListLinks(resp.result.get('links'))

        # Delete access_token
        resp = self.delete('/users/%(user)s/OS-OAUTH1/access_tokens/%(auth)s'
                           % {'user': self.user_id,
                              'auth': self.access_token.key})
        self.assertResponseStatus(resp, 204)

        # List access_token should be 0
        resp = self.get('/users/%(user_id)s/OS-OAUTH1/access_tokens'
                        % {'user_id': self.user_id})
        entities = resp.result.get('access_tokens')
        self.assertTrue(len(entities) == 0)
        self.assertValidListLinks(resp.result.get('links'))


class AuthTokenTests(OAuthFlowTests):

    def test_keystone_token_is_valid(self):
        self.test_oauth_flow()
        headers = {'X-Subject-Token': self.keystone_token_id,
                   'X-Auth-Token': self.keystone_token_id}
        r = self.get('/auth/tokens', headers=headers)
        self.assertValidTokenResponse(r, self.user)

        # now verify the oauth section
        oauth_section = r.result['token']['OS-OAUTH1']
        self.assertEquals(oauth_section['access_token_id'],
                          self.access_token.key)
        self.assertEquals(oauth_section['consumer_id'], self.consumer.key)

    def test_delete_access_token_also_revokes_token(self):
        self.test_oauth_flow()

        # Delete access token
        resp = self.delete('/users/%(user)s/OS-OAUTH1/access_tokens/%(auth)s'
                           % {'user': self.user_id,
                              'auth': self.access_token.key})
        self.assertResponseStatus(resp, 204)

        # Check Keystone Token no longer exists
        headers = {'X-Subject-Token': self.keystone_token_id,
                   'X-Auth-Token': self.keystone_token_id}
        self.get('/auth/tokens', headers=headers,
                 expected_status=401)

    def test_deleting_consumer_also_deletes_tokens(self):
        self.test_oauth_flow()

        # Delete consumer
        consumer_id = self.consumer.key
        resp = self.delete('/OS-OAUTH1/consumers/%(consumer_id)s'
                           % {'consumer_id': consumer_id})
        self.assertResponseStatus(resp, 204)

        # List access_token should be 0
        resp = self.get('/users/%(user_id)s/OS-OAUTH1/access_tokens'
                        % {'user_id': self.user_id})
        entities = resp.result.get('access_tokens')
        self.assertEqual(len(entities), 0)

        # Check Keystone Token no longer exists
        headers = {'X-Subject-Token': self.keystone_token_id,
                   'X-Auth-Token': self.keystone_token_id}
        self.head('/auth/tokens', headers=headers,
                  expected_status=401)

    def test_change_user_password_also_deletes_tokens(self):
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
        self.admin_request(path='/auth/tokens',
                           headers=headers,
                           method='GET',
                           expected_status=404)

    def test_deleting_project_also_deletes_tokens(self):
        self.test_oauth_flow()

        # delegated keystone token exists
        headers = {'X-Subject-Token': self.keystone_token_id,
                   'X-Auth-Token': self.keystone_token_id}
        r = self.get('/auth/tokens', headers=headers)
        self.assertValidTokenResponse(r, self.user)

        r = self.delete('/projects/%(project_id)s' % {
            'project_id': self.project['id']})

        headers = {'X-Subject-Token': self.keystone_token_id,
                   'X-Auth-Token': self.keystone_token_id}
        self.admin_request(path='/auth/tokens',
                           headers=headers,
                           method='GET',
                           expected_status=404)

    def test_deleting_role_also_deletes_tokens(self):
        self.skipTest('not yet written')

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
        consumer_id = consumer.get('id')
        consumer = oauth.Consumer(consumer_id, "bad_secret")
        wreq = self._wreq_create_request_token(consumer,
                                               self.role_id,
                                               self.project_id)
        self.assertRaises(RuntimeError,
                          self.controller.create_request_token,
                          {'request': wreq})

    def test_bad_request_token_key(self):
        consumer = self._create_single_consumer()
        consumer_id = consumer.get('id')
        consumer_secret = consumer.get('consumer_secret')
        consumer = oauth.Consumer(consumer_id, consumer_secret)
        wreq = self._wreq_create_request_token(consumer,
                                               self.role_id,
                                               self.project_id)
        self.controller.create_request_token({'request': wreq})
        url = self._authorize_request_token("bad_key")
        self.put(url, expected_status=404)

    def test_bad_verifier(self):
        consumer = self._create_single_consumer()
        consumer_id = consumer.get('id')
        consumer_secret = consumer.get('consumer_secret')
        consumer = oauth.Consumer(consumer_id, consumer_secret)

        wreq = self._wreq_create_request_token(consumer,
                                               self.role_id,
                                               self.project_id)
        result = self.controller.create_request_token({'request': wreq})
        credentials = urlparse.parse_qs(result)
        request_key = credentials.get('oauth_token')[0]
        request_secret = credentials.get('oauth_token_secret')[0]
        request_token = oauth.Token(request_key, request_secret)

        url = self._authorize_request_token(request_key)
        resp = self.put(url, expected_status=200)
        verifier = resp.result['token']['oauth_verifier']
        self.assertIsNotNone(verifier)

        request_token.set_verifier("bad verifier")
        wreq = self._wreq_create_access_token(consumer, request_token)
        self.assertRaises(exception.Unauthorized,
                          self.controller.create_access_token,
                          {'request': wreq})

    def test_bad_requested_roles(self):
        consumer = self._create_single_consumer()
        consumer_id = consumer.get('id')
        consumer_secret = consumer.get('consumer_secret')
        consumer = oauth.Consumer(consumer_id, consumer_secret)

        wreq = self._wreq_create_request_token(consumer,
                                               "bad_role",
                                               self.project_id)
        self.assertRaises(exception.Unauthorized,
                          self.controller.create_request_token,
                          {'request': wreq})

    def test_bad_authorizing_roles(self):
        consumer = self._create_single_consumer()
        consumer_id = consumer.get('id')
        consumer_secret = consumer.get('consumer_secret')
        consumer = oauth.Consumer(consumer_id, consumer_secret)

        wreq = self._wreq_create_request_token(consumer,
                                               self.role_id,
                                               self.project_id)
        result = self.controller.create_request_token({'request': wreq})
        credentials = urlparse.parse_qs(result)
        request_key = credentials.get('oauth_token')[0]

        self.identity_api.remove_role_from_user_and_project(self.user_id,
                                                            self.project_id,
                                                            self.role_id)
        url = self._authorize_request_token(request_key)
        self.admin_request(
            path=url,
            method='PUT',
            expected_status=404)

    def test_expired_authorizing_request_token(self):
        CONF.oauth.request_token_duration = -1

        consumer = self._create_single_consumer()
        consumer_id = consumer.get('id')
        consumer_secret = consumer.get('consumer_secret')
        self.consumer = oauth.Consumer(consumer_id, consumer_secret)
        self.assertIsNotNone(self.consumer.key)

        wreq = self._wreq_create_request_token(self.consumer,
                                               self.role_id,
                                               self.project_id)
        result = self.controller.create_request_token({'request': wreq})
        credentials = urlparse.parse_qs(result)
        request_key = credentials.get('oauth_token')[0]
        request_secret = credentials.get('oauth_token_secret')[0]
        self.request_token = oauth.Token(request_key, request_secret)
        self.assertIsNotNone(self.request_token.key)

        url = self._authorize_request_token(request_key)
        self.put(url, expected_status=401)

    def test_expired_creating_keystone_token(self):
        CONF.oauth.access_token_duration = -1
        consumer = self._create_single_consumer()
        consumer_id = consumer.get('id')
        consumer_secret = consumer.get('consumer_secret')
        self.consumer = oauth.Consumer(consumer_id, consumer_secret)
        self.assertIsNotNone(self.consumer.key)

        wreq = self._wreq_create_request_token(self.consumer,
                                               self.role_id,
                                               self.project_id)
        result = self.controller.create_request_token({'request': wreq})
        credentials = urlparse.parse_qs(result)
        request_key = credentials.get('oauth_token')[0]
        request_secret = credentials.get('oauth_token_secret')[0]
        self.request_token = oauth.Token(request_key, request_secret)
        self.assertIsNotNone(self.request_token.key)

        url = self._authorize_request_token(request_key)
        resp = self.put(url, expected_status=200)
        self.verifier = resp.result['token']['oauth_verifier']

        self.request_token.set_verifier(self.verifier)
        wreq = self._wreq_create_access_token(self.consumer,
                                              self.request_token)

        result = self.controller.create_access_token({'request': wreq})
        credentials = urlparse.parse_qs(result)
        access_key = credentials.get('oauth_token')[0]
        access_secret = credentials.get('oauth_token_secret')[0]
        self.access_token = oauth.Token(access_key, access_secret)
        self.assertIsNotNone(self.access_token.key)

        headers = {'Content-Type': 'application/json'}
        body = {'auth': {'identity': {'methods': [], 'oauth':
                                     {'access_token_id': {}}},
                         'scope': {'project': {'id': {}}}
                         }
                }
        body['auth']['identity']['methods'].append('oauth')
        body['auth']['identity']['oauth']['access_token_id'] = access_key
        body['auth']['scope']['project']['id'] = self.project_id

        # this is kind of a hack
        url = 'http://localhost:80/auth/tokens'
        oreq = self._oauth_request(
            consumer=self.consumer, token=self.access_token,
            http_method='POST',
            http_url=url)
        hmac = oauth.SignatureMethod_HMAC_SHA1()
        oreq.sign_request(hmac, self.consumer, self.access_token)
        headers.update(oreq.to_header())
        self.admin_request(
            method='POST',
            headers=headers,
            path='/v3/auth/tokens',
            body=body,
            expected_status=401)
