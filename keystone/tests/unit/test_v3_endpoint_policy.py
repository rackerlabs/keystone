# Copyright 2014 IBM Corp.
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

import calendar
import datetime
import mock
from testtools import matchers
import uuid

from oslo_config import cfg

from keystone.tests.unit import test_v3


CONF = cfg.CONF


class EndpointPolicyTestCase(test_v3.RestfulTestCase):
    """Test endpoint policy CRUD.

    In general, the controller layer of the endpoint policy extension is really
    just marshalling the data around the underlying manager calls. Given that
    the manager layer is tested in depth by the backend tests, the tests we
    execute here concentrate on ensuring we are correctly passing and
    presenting the data.

    """

    def setUp(self):
        super(EndpointPolicyTestCase, self).setUp()
        self.policy = self.new_policy_ref()
        self.policy_api.create_policy(self.policy['id'], self.policy)
        self.service = self.new_service_ref()
        self.catalog_api.create_service(self.service['id'], self.service)
        self.endpoint = self.new_endpoint_ref(self.service['id'], enabled=True)
        self.catalog_api.create_endpoint(self.endpoint['id'], self.endpoint)
        self.region = self.new_region_ref()
        self.catalog_api.create_region(self.region)

    def assert_head_and_get_return_same_response(self, url, expected_status):
        self.get(url, expected_status=expected_status)
        self.head(url, expected_status=expected_status)

    # endpoint policy crud tests
    def _crud_test(self, url):
        # Test when the resource does not exist also ensures
        # that there is not a false negative after creation.

        self.assert_head_and_get_return_same_response(url, expected_status=404)

        self.put(url, expected_status=204)

        # test that the new resource is accessible.
        self.assert_head_and_get_return_same_response(url, expected_status=204)

        self.delete(url, expected_status=204)

        # test that the deleted resource is no longer accessible
        self.assert_head_and_get_return_same_response(url, expected_status=404)

    def test_crud_for_policy_for_explicit_endpoint(self):
        """PUT, HEAD and DELETE for explicit endpoint policy."""

        url = ('/policies/%(policy_id)s/OS-ENDPOINT-POLICY'
               '/endpoints/%(endpoint_id)s') % {
                   'policy_id': self.policy['id'],
                   'endpoint_id': self.endpoint['id']}
        self._crud_test(url)

    def test_crud_for_policy_for_service(self):
        """PUT, HEAD and DELETE for service endpoint policy."""

        url = ('/policies/%(policy_id)s/OS-ENDPOINT-POLICY'
               '/services/%(service_id)s') % {
                   'policy_id': self.policy['id'],
                   'service_id': self.service['id']}
        self._crud_test(url)

    def test_crud_for_policy_for_region_and_service(self):
        """PUT, HEAD and DELETE for region and service endpoint policy."""

        url = ('/policies/%(policy_id)s/OS-ENDPOINT-POLICY'
               '/services/%(service_id)s/regions/%(region_id)s') % {
                   'policy_id': self.policy['id'],
                   'service_id': self.service['id'],
                   'region_id': self.region['id']}
        self._crud_test(url)

    def test_get_policy_for_endpoint(self):
        """GET /endpoints/{endpoint_id}/policy."""

        self.put('/policies/%(policy_id)s/OS-ENDPOINT-POLICY'
                 '/endpoints/%(endpoint_id)s' % {
                     'policy_id': self.policy['id'],
                     'endpoint_id': self.endpoint['id']},
                 expected_status=204)

        self.head('/endpoints/%(endpoint_id)s/OS-ENDPOINT-POLICY'
                  '/policy' % {
                      'endpoint_id': self.endpoint['id']},
                  expected_status=200)

        r = self.get('/endpoints/%(endpoint_id)s/OS-ENDPOINT-POLICY'
                     '/policy' % {
                         'endpoint_id': self.endpoint['id']},
                     expected_status=200)
        self.assertValidPolicyResponse(r, ref=self.policy)

    def test_list_endpoints_for_policy(self):
        """GET /policies/%(policy_id}/endpoints."""

        self.put('/policies/%(policy_id)s/OS-ENDPOINT-POLICY'
                 '/endpoints/%(endpoint_id)s' % {
                     'policy_id': self.policy['id'],
                     'endpoint_id': self.endpoint['id']},
                 expected_status=204)

        r = self.get('/policies/%(policy_id)s/OS-ENDPOINT-POLICY'
                     '/endpoints' % {
                         'policy_id': self.policy['id']},
                     expected_status=200)
        self.assertValidEndpointListResponse(r, ref=self.endpoint)
        self.assertThat(r.result.get('endpoints'), matchers.HasLength(1))

    def test_endpoint_association_cleanup_when_endpoint_deleted(self):
        url = ('/policies/%(policy_id)s/OS-ENDPOINT-POLICY'
               '/endpoints/%(endpoint_id)s') % {
                   'policy_id': self.policy['id'],
                   'endpoint_id': self.endpoint['id']}

        self.put(url, expected_status=204)
        self.head(url, expected_status=204)

        self.delete('/endpoints/%(endpoint_id)s' % {
            'endpoint_id': self.endpoint['id']})

        self.head(url, expected_status=404)

    def test_region_service_association_cleanup_when_region_deleted(self):
        url = ('/policies/%(policy_id)s/OS-ENDPOINT-POLICY'
               '/services/%(service_id)s/regions/%(region_id)s') % {
                   'policy_id': self.policy['id'],
                   'service_id': self.service['id'],
                   'region_id': self.region['id']}

        self.put(url, expected_status=204)
        self.head(url, expected_status=204)

        self.delete('/regions/%(region_id)s' % {
            'region_id': self.region['id']})

        self.head(url, expected_status=404)

    def test_region_service_association_cleanup_when_service_deleted(self):
        url = ('/policies/%(policy_id)s/OS-ENDPOINT-POLICY'
               '/services/%(service_id)s/regions/%(region_id)s') % {
                   'policy_id': self.policy['id'],
                   'service_id': self.service['id'],
                   'region_id': self.region['id']}

        self.put(url, expected_status=204)
        self.head(url, expected_status=204)

        self.delete('/services/%(service_id)s' % {
            'service_id': self.service['id']})

        self.head(url, expected_status=404)

    def test_service_association_cleanup_when_service_deleted(self):
        url = ('/policies/%(policy_id)s/OS-ENDPOINT-POLICY'
               '/services/%(service_id)s') % {
                   'policy_id': self.policy['id'],
                   'service_id': self.service['id']}

        self.put(url, expected_status=204)
        self.get(url, expected_status=204)

        self.delete('/policies/%(policy_id)s' % {
            'policy_id': self.policy['id']})

        self.head(url, expected_status=404)

    def test_service_association_cleanup_when_policy_deleted(self):
        url = ('/policies/%(policy_id)s/OS-ENDPOINT-POLICY'
               '/services/%(service_id)s') % {
                   'policy_id': self.policy['id'],
                   'service_id': self.service['id']}

        self.put(url, expected_status=204)
        self.get(url, expected_status=204)

        self.delete('/services/%(service_id)s' % {
            'service_id': self.service['id']})

        self.head(url, expected_status=404)

    def test_policy_cache_control_header(self):
        url = ('/policies/%(policy_id)s/OS-ENDPOINT-POLICY'
               '/services/%(service_id)s') % {
                   'policy_id': self.policy['id'],
                   'service_id': self.service['id']}
        self.put(url, expected_status=204)

        url = '/endpoints/%s/OS-ENDPOINT-POLICY/policy' % self.endpoint['id']
        response = self.get(url)

        self.assertIn('Cache-Control', response.headers)
        max_age = response.headers['Cache-Control']
        self.assertEqual('max-age=', max_age[:8])
        self.assertTrue(int(max_age[8:]) <= CONF.policy.policy_timeout)

    def _test_policy_caching(self, endpoint_id, freshness):
        """Associate, retrieve and check policy freshness for endpoint."""

        url = ('/policies/%(policy_id)s/OS-ENDPOINT-POLICY'
               '/services/%(service_id)s') % {
                   'policy_id': self.policy['id'],
                   'service_id': self.service['id']}
        self.put(url, expected_status=204)

        url = '/endpoints/%s/OS-ENDPOINT-POLICY/policy' % endpoint_id
        response = self.get(url)

        max_age = response.headers['Cache-Control']
        # Cache-Control value is in the format max-age={freshness}
        max_age = int(max_age[8:])
        self.assertEqual(freshness, max_age)

        policy = response.result['policy']
        policy.pop('links')
        self.assertEqual(self.policy, policy)

    @mock.patch('oslo_utils.timeutils.utcnow')
    @mock.patch('oslo_utils.timeutils.utcnow_ts')
    def test_policy_cache_thundering_herd(self, utcnow_ts, utcnow):
        '''Test freshness vary for policies associated with different endpoints

        In this scenario, requests for the policies associated with 3 different
        endpoints arrive at the same time in the server.

        Configuration:
        - The policy_timeout is 300 seconds, implying that the server times out
        every 5 minutes;
        - It's 12:02:00, and the last time the server timed out was 12:00:00.

        Test plan for the 1st request:
        - The hash (endpoint_id % policy_timeout) equals to 120 seconds,
        meaning the policy for this endpoint expired at 12:02:00 (right now);
        - Thus, the returned policy will be valid until 12:07:00, i.e it is
        fresh for 300 seconds from now.

        Test plan for the 2nd request:
        - The hash (endpoint_id % policy_timeout) equals to 121 seconds,
        meaning the policy for this endpoint expired at 12:02:01;
        - Thus, the returned policy will be valid until 12:02:01, i.e it is
        fresh for 1 second from now.

        Test plan for the 3rd request:
        - The hash (endpoint_id % policy_timeout) equals to 119 seconds,
        meaning the policy for this endpoint expired at 12:01:59;
        - Thus, the returned policy will be valid until 12:06:59, i.e it is
        fresh for 299 seconds from now.

        '''

        # Let's use the Liberty Release (2015.2.0) date as base for this test
        date = {'year': 2015, 'month': 10, 'day': 15}

        utcnow.return_value = datetime.datetime(
            hour=12, minute=2, second=0, **date)
        utcnow_ts.return_value = calendar.timegm(
            utcnow.return_value.timetuple())

        hashes = (120, 121, 119)
        freshness = (300, 1, 299)

        for i in range(len(hashes)):
            endpoint = {'id': uuid.UUID(int=hashes[i]).hex,
                        'interface': 'public',
                        'region_id': self.region['id'],
                        'service_id': self.service['id'],
                        'url': '/url'}
            self.catalog_api.create_endpoint(endpoint['id'], endpoint)

            self._test_policy_caching(endpoint['id'], freshness[i])

    @mock.patch('oslo_utils.timeutils.utcnow')
    @mock.patch('oslo_utils.timeutils.utcnow_ts')
    def test_policy_cache_inconsistency(self, utcnow_ts, utcnow):
        '''Test policy updates may cause inconsistency between endpoints

        In this scenario, two endpoints request the same policy entity at
        different times. In the meantime, a policy update occurs, and the
        second endpoint gets the changes in its request. The policy of the
        first endpoint remains out-of-date until it expires.

        Configuration:
        - The policy_timeout is 300 seconds, implying that the server times out
        every 5 minutes;
        - The hash (endpoint_id % policy_timeou) equals to 0 seconds, meaning
        the policy for this endpoint expires exactly when the server times out.

        Test plan for the 1st request:
        - It's 12:02:00 and the next server timeout will be at 12:05:00;
        - The first endpoint requests the policy and it will be valid until
        12:05:00, i.e it is fresh for 180 seconds.

        There is a policy update somewhen between 12:02:00 and 12:04:00.

        Test plan for the 2nd request:
        - It's 12:04:00 and the next server timeout will be at 12:05:00;
        - The second endpoint requests the policy and gets the updated entity,
        which will be valid until 12:05:00, i.e it is fresh for 60 seconds.

        '''

        endpoint = {'id': uuid.UUID(int=0).hex,
                    'interface': 'public',
                    'region_id': self.region['id'],
                    'service_id': self.service['id'],
                    'url': '/url'}
        self.catalog_api.create_endpoint(endpoint['id'], endpoint)

        # Let's use the Liberty Release (2015.2.0) date as base for this test
        date = {'year': 2015, 'month': 10, 'day': 15}

        utcnow.return_value = datetime.datetime(hour=12, minute=2, **date)
        utcnow_ts.return_value = calendar.timegm(
            utcnow.return_value.timetuple())
        self._test_policy_caching(endpoint['id'], 180)

        self.policy['blob'] = uuid.uuid4().hex
        self.policy_api.update_policy(self.policy['id'], self.policy)

        utcnow.return_value = datetime.datetime(hour=12, minute=4, **date)
        utcnow_ts.return_value = calendar.timegm(
            utcnow.return_value.timetuple())
        self._test_policy_caching(endpoint['id'], 60)


class JsonHomeTests(test_v3.JsonHomeTestMixin):
    EXTENSION_LOCATION = ('http://docs.openstack.org/api/openstack-identity/3/'
                          'ext/OS-ENDPOINT-POLICY/1.0/rel')
    PARAM_LOCATION = 'http://docs.openstack.org/api/openstack-identity/3/param'

    JSON_HOME_DATA = {
        EXTENSION_LOCATION + '/endpoint_policy': {
            'href-template': '/endpoints/{endpoint_id}/OS-ENDPOINT-POLICY/'
                             'policy',
            'href-vars': {
                'endpoint_id': PARAM_LOCATION + '/endpoint_id',
            },
        },
        EXTENSION_LOCATION + '/policy_endpoints': {
            'href-template': '/policies/{policy_id}/OS-ENDPOINT-POLICY/'
                             'endpoints',
            'href-vars': {
                'policy_id': PARAM_LOCATION + '/policy_id',
            },
        },
        EXTENSION_LOCATION + '/endpoint_policy_association': {
            'href-template': '/policies/{policy_id}/OS-ENDPOINT-POLICY/'
                             'endpoints/{endpoint_id}',
            'href-vars': {
                'policy_id': PARAM_LOCATION + '/policy_id',
                'endpoint_id': PARAM_LOCATION + '/endpoint_id',
            },
        },
        EXTENSION_LOCATION + '/service_policy_association': {
            'href-template': '/policies/{policy_id}/OS-ENDPOINT-POLICY/'
                             'services/{service_id}',
            'href-vars': {
                'policy_id': PARAM_LOCATION + '/policy_id',
                'service_id': PARAM_LOCATION + '/service_id',
            },
        },
        EXTENSION_LOCATION + '/region_and_service_policy_association': {
            'href-template': '/policies/{policy_id}/OS-ENDPOINT-POLICY/'
                             'services/{service_id}/regions/{region_id}',
            'href-vars': {
                'policy_id': PARAM_LOCATION + '/policy_id',
                'service_id': PARAM_LOCATION + '/service_id',
                'region_id': PARAM_LOCATION + '/region_id',
            },
        },
    }
