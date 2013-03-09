# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>
#
# Author: Chmouel Boudjnah <chmouel@enovance.com>
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
import socket

import unittest2 as unittest
import webob

from keystone.middleware import ec2_token
from keystone.openstack.common import jsonutils


class FakeHTTPResponse(object):
    def __init__(self, status, body):
        self.status = status
        self.body = body
        self.reason = ""

    def read(self):
        return self.body


class FakeHTTPConnection(object):
    def __init__(self, *args):
        return

    def getresponse(self):
        return self.resp

    def close(self):
        pass

    def request(self, method, path, **kwargs):
        pass


class FakeApp(object):
    """This represents a WSGI app protected by the auth_token middleware."""
    def __init__(self, headers=[]):
        self.headers = headers

    def __call__(self, env, start_response):
        req = webob.Request(env)
        return webob.Response(
            headers=req.headers, status='200 OK')(env, start_response)


class FakeMemcache(object):
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, time=0):
        self.store[key] = value
        return True


class Ec2TokenMiddlewareTestBase(unittest.TestCase):
    def setUp(self):
        super(Ec2TokenMiddlewareTestBase, self).setUp()
        self.middleware = ec2_token.EC2Token(FakeApp(), {})
        self.middleware.http_client_class = FakeHTTPConnection
        self.middleware._cache_initialized = True
        self.middleware._cache = FakeMemcache()

    def start_fake_response(self, status, headers):
        self.response_status = int(status.split(' ', 1)[0])
        self.response_headers = dict(headers)


class Ec2TokenMiddlewareTestBad(Ec2TokenMiddlewareTestBase):
    def test_bad_request(self):
        query = '/?Signature=signature'
        req = webob.Request.blank(query)
        self.middleware(req.environ, self.start_fake_response)
        self.assertEqual(self.response_status, 400)

    def test_bad_reply_json(self):
        def bad_json(cls, method, path, **kwargs):
            cls.status = 201
            body = jsonutils.dumps({'foo': 'bar'})
            cls.resp = FakeHTTPResponse(cls.status, body)

        self.middleware.http_client_class.request = bad_json
        query = '/?Signature=signature&AWSAccessKeyId=accessid'
        req = webob.Request.blank(query)
        self.middleware(req.environ, self.start_fake_response)
        self.assertEqual(self.response_status, 400)

    def test_bad_reply_not_json(self):
        def bad_not_json(cls, method, path, **kwargs):
            cls.status = 201
            body = jsonutils.dumps("\o-o/")
            cls.resp = FakeHTTPResponse(cls.status, body)

        self.middleware.http_client_class.request = bad_not_json
        query = '/?Signature=signature&AWSAccessKeyId=accessid'
        req = webob.Request.blank(query)
        self.middleware(req.environ, self.start_fake_response)
        self.assertEqual(self.response_status, 400)

    def test_bad_cnx_error(self):
        def bad_cnx_error(cls, method, path, **kwargs):
            raise socket.error

        self.middleware.http_client_class.request = bad_cnx_error
        query = '/?Signature=signature&AWSAccessKeyId=accessid'
        req = webob.Request.blank(query)
        self.middleware(req.environ, self.start_fake_response)
        self.assertEqual(self.response_status, 400)


class Ec2TokenMiddlewareTestGood(Ec2TokenMiddlewareTestBase):
    def test_good_request_uncached(self):
        token = 'GOOD_TOKEN'

        def good_request(cls, method, path, **kwargs):
            cls.status = 201
            ret = {'access': {'token':
                              {'id': token,
                               'tenant': {'id': 'TENANT_ID'}}}}
            body = jsonutils.dumps(ret)
            cls.resp = FakeHTTPResponse(cls.status, body)

        self.middleware.http_client_class.request = good_request
        query = '/?Signature=signature&AWSAccessKeyId=accessid'
        req = webob.Request.blank(query)
        self.middleware(req.environ, self.start_fake_response)
        self.assertEqual(self.response_status, 200)
        self.assertIn('X-Auth-Token', self.response_headers)
        self.assertEqual(self.response_headers['X-Auth-Token'], token)

    def test_good_request_cached(self):
        token = 'CACHED_TOKEN'
        cached = {'access': {'token':
                             {'id': token,
                              'tenant': {'id': 'TENANT_ID'}}}}
        self.middleware._cache.set('ec2Signature-signature', cached)

        query = '/?Signature=signature&AWSAccessKeyId=accessid'
        req = webob.Request.blank(query)
        self.middleware(req.environ, self.start_fake_response)
        self.assertEqual(self.response_status, 200)
        self.assertIn('X-Auth-Token', self.response_headers)
        self.assertEqual(self.response_headers['X-Auth-Token'], token)
