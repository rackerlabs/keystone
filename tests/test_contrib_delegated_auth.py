# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
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

import webob

from keystone import test
from keystone.common import oauth
from keystone.contrib.delegated_auth import core as delegated_auth

import test_v3
import uuid


class OauthFlowTest(test.TestCase):
    def _wsgi_request(self, *args, **kw):
        return webob.Request.blank(*args, **kw)

    def _oauth_request(self, consumer, token=None, **kw):
        return oauth.Request.from_consumer_and_token(consumer=consumer,
                                                     token=token,
                                                     **kw)

    def setUp(self):
        super(OauthFlowTest, self).setUp()
        self.controller = delegated_auth.OauthFlowManiaV3()
        self.consumer = oauth.Consumer('foo-key', 'foo-secret')
        self.base_url = 'https://localhost:5000'

    def test_request_token(self):
        oreq = self._oauth_request(
            consumer=self.consumer,
            http_url=self.base_url + '/oauth/request_token',
            parameters={'requested_roles': 'flippyfloppy'})
        oreq.sign_request(
            oauth.SignatureMethod_HMAC_SHA1(), self.consumer, None)
        wreq = self._wsgi_request(oreq.to_url())
        print wreq

        token = self.controller.create_request_token(context={'request': wreq})


class ConsumerCRUDTest(test_v3.RestfulTestCase):
    def setUp(self):
        super(ConsumerCRUDTest, self).setUp()

    def test_create_consumers(self):
        """POST /DA/consumer"""
        ref = self.new_consumer_ref(False)
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
        create_ref = self.new_consumer_ref(False)
        create_resp = self.post(
            '/DA/consumer',
            body={'consumer': create_ref})
        consumer = create_resp.body.get('consumer')
        name = consumer.get('name')
        id = consumer.get('id')
        key = consumer.get('consumer_key')
        secret = consumer.get('consumer_secret')

        update_ref = create_resp.body.get('consumer')
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
        create_ref = self.new_consumer_ref(False)
        create_resp = self.post(
            '/DA/consumer',
            body={'consumer': create_ref})
        id = create_resp.body.get('consumer').get('id')

        delete_resp = self.delete('/DA/delete_consumer/%(consumer_id)s'
                                  % {'consumer_id': id})
        self.assertResponseStatus(delete_resp, 204)

    def test_get_consumer(self):
        """GET /DA/consumer/{consumer_id}"""
        create_ref = self.new_consumer_ref(False)
        create_resp = self.post(
            '/DA/consumer',
            body={'consumer': create_ref})
        id = create_resp.body.get('consumer').get('id')

        delete_resp = self.get('/DA/consumer/%(consumer_id)s'
                                  % {'consumer_id': id})
        self.assertTrue(delete_resp.body.get('consumer').get('id'), id)

    def new_consumer_ref(self, all_fields):
        return {'name': uuid.uuid4().hex}
