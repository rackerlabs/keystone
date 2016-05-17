# Copyright 2013 OpenStack Foundation
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json
import mock
import requests
import urllib
import uuid

from six.moves import http_client

from keystone.tests import unit
from keystone.tests.unit import test_v3


class PolicyTestCase(test_v3.RestfulTestCase):
    """Test policy CRUD."""

    def setUp(self):
        super(PolicyTestCase, self).setUp()
        self.policy = unit.new_policy_ref()
        self.policy_id = self.policy['id']
        self.policy_api.create_policy(
            self.policy_id,
            self.policy.copy())

    # policy crud tests

    def test_create_policy(self):
        """Call ``POST /policies``."""
        ref = unit.new_policy_ref()
        r = self.post('/policies', body={'policy': ref})
        return self.assertValidPolicyResponse(r, ref)

    def test_list_head_policies(self):
        """Call ``GET & HEAD /policies``."""
        resource_url = '/policies'
        r = self.get(resource_url)
        self.assertValidPolicyListResponse(r, ref=self.policy)
        self.head(resource_url, expected_status=http_client.OK)

    def test_get_head_policy(self):
        """Call ``GET & HEAD /policies/{policy_id}``."""
        resource_url = ('/policies/%(policy_id)s' %
                        {'policy_id': self.policy_id})
        r = self.get(resource_url)
        self.assertValidPolicyResponse(r, self.policy)
        self.head(resource_url, expected_status=http_client.OK)

    def test_update_policy(self):
        """Call ``PATCH /policies/{policy_id}``."""
        self.policy['blob'] = json.dumps({'data': uuid.uuid4().hex, })
        r = self.patch(
            '/policies/%(policy_id)s' % {'policy_id': self.policy_id},
            body={'policy': self.policy})
        self.assertValidPolicyResponse(r, self.policy)

    def test_delete_policy(self):
        """Call ``DELETE /policies/{policy_id}``."""
        self.delete(
            '/policies/%(policy_id)s' % {'policy_id': self.policy_id})


class PolicyEnforcementTestCase(test_v3.RestfulTestCase):

    def create_scoped_token(self):
        body = {
            'auth': {
                'identity': {
                    'methods': ['password'],
                    'password': {
                        'user': {
                            'name': self.user['name'],
                            'password': self.user['password'],
                            'domain': {
                                'id': self.user['domain_id']
                            }
                        }
                    }
                },
                'scope': {
                    'project': {
                        'id': self.project['id'],
                    }
                }
            }
        }
        return self.v3_create_token(auth=body)

    def test_check_policy_true(self):
        resource_url = '/policy_enforcement/identity:list_policies'

        credentials = {"roles": ["admin"]}
        body = {'credentials': json.dumps(credentials),
                'target': '{}'}

        body_encoded = urllib.urlencode(body)
        resp = self.request(method='POST',
                            path=resource_url,
                            body=body_encoded,
                            accept='*/*',
                            app=self.public_app,
                            content_type='application/x-www-form-urlencoded')
        self.assertEqual('True', resp.body)

    def test_check_policy_false(self):
        resource_url = '/policy_enforcement/identity:list_policies'

        credentials = {"roles": ["user"]}
        body = {'credentials': json.dumps(credentials),
                'target': '{}'}

        body_encoded = urllib.urlencode(body)
        resp = self.request(method='POST',
                            path=resource_url,
                            body=body_encoded,
                            accept='*/*',
                            app=self.public_app,
                            content_type='application/x-www-form-urlencoded')
        self.assertEqual('False', resp.body)

    @mock.patch('requests.post')
    def test_list_policy_url(self, mock_post):

        class Post_response(object):
            text = 'True'

            def close(self):
                pass

        mock_post.return_value = Post_response()

        token = self.create_scoped_token()
        self.get('/policies', token=token.headers.get('X-Subject-Token'))

        args, kwargs = mock_post.call_args
        url_arg = args[0]
        data_arg = kwargs['data']
        credentials_arg = json.loads(data_arg['credentials'])
        token_arg = credentials_arg['token']

        token_body = json.loads(token.body)['token']
        url = 'http://localhost:5000/policy_enforcement/identity:list_policies'

        self.assertEqual(url, url_arg)
        self.assertEqual(token_body, token_arg)
        self.assertEqual('{}', data_arg['target'])
