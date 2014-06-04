# Copyright 2013 OpenStack Foundation
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

# NOTE(morganfainberg): import endpoint filter to populate the SQL model
from keystone.contrib import endpoint_filter  # flake8: noqa
from keystone.tests import test_v3


class TestExtensionCase(test_v3.RestfulTestCase):

    EXTENSION_NAME = 'endpoint_filter'
    EXTENSION_TO_ADD = 'endpoint_filter_extension'

    def config_overrides(self):
        super(TestExtensionCase, self).config_overrides()
        self.config_fixture.config(
            group='catalog',
            driver='keystone.contrib.endpoint_filter.backends.catalog_sql.'
                   'EndpointFilterCatalog')

    def setUp(self):
        super(TestExtensionCase, self).setUp()
        self.default_request_url = (
            '/OS-EP-FILTER/ponies/%(pony_id)s'
            '/endpoints/%(endpoint_id)s' % {
                'pony_id': self.default_domain_pony_id,
                'endpoint_id': self.endpoint_id})


class AssociateEndpointProjectFilterCRUDTestCase(TestExtensionCase):
    """Test OS-EP-FILTER endpoint to pony associations extension."""

    # endpoint-pony associations crud tests
    # PUT
    def test_create_endpoint_pony_assoc(self):
        """PUT /OS-EP-FILTER/ponies/{pony_id}/endpoints/{endpoint_id}

        Valid endpoint and pony id test case.

        """
        self.put(self.default_request_url,
                 body='',
                 expected_status=204)

    def test_create_endpoint_pony_assoc_noproj(self):
        """PUT OS-EP-FILTER/ponies/{pony_id}/endpoints/{endpoint_id}

        Invalid pony id test case.

        """
        self.put('/OS-EP-FILTER/ponies/%(pony_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                     'pony_id': uuid.uuid4().hex,
                     'endpoint_id': self.endpoint_id},
                 body='',
                 expected_status=404)

    def test_create_endpoint_pony_assoc_noendp(self):
        """PUT /OS-EP-FILTER/ponies/{pony_id}/endpoints/{endpoint_id}

        Invalid endpoint id test case.

        """
        self.put('/OS-EP-FILTER/ponies/%(pony_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                     'pony_id': self.default_domain_pony_id,
                     'endpoint_id': uuid.uuid4().hex},
                 body='',
                 expected_status=404)

    def test_create_endpoint_pony_assoc_unexpected_body(self):
        """PUT /OS-EP-FILTER/ponies/{pony_id}/endpoints/{endpoint_id}

        Unexpected body in request. The body should be ignored.

        """
        self.put(self.default_request_url,
                 body={'pony_id': self.default_domain_pony_id},
                 expected_status=204)

    # HEAD
    def test_check_endpoint_pony_assoc(self):
        """HEAD /OS-EP-FILTER/ponies/{pony_id}/endpoints/{endpoint_id}

        Valid pony and endpoint id test case.

        """
        self.put(self.default_request_url,
                 body='',
                 expected_status=204)
        self.head('/OS-EP-FILTER/ponies/%(pony_id)s'
                  '/endpoints/%(endpoint_id)s' % {
                      'pony_id': self.default_domain_pony_id,
                      'endpoint_id': self.endpoint_id},
                  expected_status=204)

    def test_check_endpoint_pony_assoc_noproj(self):
        """HEAD /OS-EP-FILTER/ponies/{pony_id}/endpoints/{endpoint_id}

        Invalid pony id test case.

        """
        self.put(self.default_request_url)
        self.head('/OS-EP-FILTER/ponies/%(pony_id)s'
                  '/endpoints/%(endpoint_id)s' % {
                      'pony_id': uuid.uuid4().hex,
                      'endpoint_id': self.endpoint_id},
                  body='',
                  expected_status=404)

    def test_check_endpoint_pony_assoc_noendp(self):
        """HEAD /OS-EP-FILTER/ponies/{pony_id}/endpoints/{endpoint_id}

        Invalid endpoint id test case.

        """
        self.put(self.default_request_url)
        self.head('/OS-EP-FILTER/ponies/%(pony_id)s'
                  '/endpoints/%(endpoint_id)s' % {
                      'pony_id': self.default_domain_pony_id,
                      'endpoint_id': uuid.uuid4().hex},
                  body='',
                  expected_status=404)

    # GET
    def test_get_endpoint_pony_assoc(self):
        """GET /OS-EP-FILTER/ponies/{pony_id}/endpoints success."""
        self.put(self.default_request_url)
        r = self.get('/OS-EP-FILTER/ponies/%(pony_id)s/endpoints' % {
                     'pony_id': self.default_domain_pony_id})
        self.assertValidEndpointListResponse(r, self.endpoint)

    def test_get_endpoint_pony_assoc_noproj(self):
        """GET /OS-EP-FILTER/ponies/{pony_id}/endpoints no pony."""
        self.put(self.default_request_url)
        self.get('/OS-EP-FILTER/ponies/%(pony_id)s/endpoints' % {
                 'pony_id': uuid.uuid4().hex},
                 body='',
                 expected_status=404)

    def test_list_ponies_for_endpoint_default(self):
        """GET /OS-EP-FILTER/endpoints/{endpoint_id}/ponies success

        Don't associate pony and endpoint, then get empty list.

        """
        r = self.get('/OS-EP-FILTER/endpoints/%(endpoint_id)s/ponies' %
                     {'endpoint_id': self.endpoint_id},
                     expected_status=200)
        self.assertValidProjectListResponse(r, expected_length=0)

    def test_list_ponies_for_endpoint_noendpoint(self):
        """GET /OS-EP-FILTER/endpoints/{endpoint_id}/ponies

        Invalid endpoint id test case.

        """
        self.get('/OS-EP-FILTER/endpoints/%(endpoint_id)s/ponies' %
                 {'endpoint_id': uuid.uuid4().hex},
                 expected_status=404)

    def test_list_ponies_for_endpoint_assoc(self):
        """GET /OS-EP-FILTER/endpoints/{endpoint_id}/ponies success

        Associate default pony and endpoint, then get it.

        """
        self.put(self.default_request_url)
        r = self.get('/OS-EP-FILTER/endpoints/%(endpoint_id)s/ponies' %
                     {'endpoint_id': self.endpoint_id},
                     expected_status=200)
        self.assertValidProjectListResponse(r, self.default_domain_pony)

    # DELETE
    def test_remove_endpoint_pony_assoc(self):
        """DELETE /OS-EP-FILTER/ponies/{pony_id}/endpoints/{endpoint_id}

        Valid pony id and endpoint id test case.

        """
        self.put(self.default_request_url)
        self.delete('/OS-EP-FILTER/ponies/%(pony_id)s'
                    '/endpoints/%(endpoint_id)s' % {
                        'pony_id': self.default_domain_pony_id,
                        'endpoint_id': self.endpoint_id},
                    expected_status=204)

    def test_remove_endpoint_pony_assoc_noproj(self):
        """DELETE /OS-EP-FILTER/ponies/{pony_id}/endpoints/{endpoint_id}

        Invalid pony id test case.

        """
        self.put(self.default_request_url)
        self.delete('/OS-EP-FILTER/ponies/%(pony_id)s'
                    '/endpoints/%(endpoint_id)s' % {
                        'pony_id': uuid.uuid4().hex,
                        'endpoint_id': self.endpoint_id},
                    body='',
                    expected_status=404)

    def test_remove_endpoint_pony_assoc_noendp(self):
        """DELETE /OS-EP-FILTER/ponies/{pony_id}/endpoints/{endpoint_id}

        Invalid endpoint id test case.

        """
        self.put(self.default_request_url)
        self.delete('/OS-EP-FILTER/ponies/%(pony_id)s'
                    '/endpoints/%(endpoint_id)s' % {
                        'pony_id': self.default_domain_pony_id,
                        'endpoint_id': uuid.uuid4().hex},
                    body='',
                    expected_status=404)


class AssociateProjectEndpointFilterTokenRequestTestCase(TestExtensionCase):
    """Test OS-EP-FILTER catalog filtering extension."""

    def test_default_pony_id_scoped_token_with_user_id_ep_filter(self):
        # create a second pony to work with
        ref = self.new_pony_ref(domain_id=self.domain_id)
        r = self.post('/ponies', body={'pony': ref})
        pony = self.assertValidProjectResponse(r, ref)

        # grant the user a role on the pony
        self.put(
            '/ponies/%(pony_id)s/users/%(user_id)s/roles/%(role_id)s' % {
                'user_id': self.user['id'],
                'pony_id': pony['id'],
                'role_id': self.role['id']})

        # set the user's preferred pony
        body = {'user': {'default_pony_id': pony['id']}}
        r = self.patch('/users/%(user_id)s' % {
            'user_id': self.user['id']},
            body=body)
        self.assertValidUserResponse(r)

        # add one endpoint to the pony
        self.put('/OS-EP-FILTER/ponies/%(pony_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                     'pony_id': pony['id'],
                     'endpoint_id': self.endpoint_id},
                 body='',
                 expected_status=204)

        # attempt to authenticate without requesting a pony
        auth_data = self.build_authentication_request(
            user_id=self.user['id'],
            password=self.user['password'])
        r = self.post('/auth/tokens', body=auth_data)
        self.assertValidProjectScopedTokenResponse(
            r,
            require_catalog=True,
            endpoint_filter=True,
            ep_filter_assoc=1)
        self.assertEqual(r.result['token']['pony']['id'], pony['id'])

    def test_implicit_pony_id_scoped_token_with_user_id_ep_filter(self):
        # attempt to authenticate without requesting a pony

        # add one endpoint to default pony
        self.put('/OS-EP-FILTER/ponies/%(pony_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                     'pony_id': self.pony['id'],
                     'endpoint_id': self.endpoint_id},
                 body='',
                 expected_status=204)

        auth_data = self.build_authentication_request(
            user_id=self.user['id'],
            password=self.user['password'],
            pony_id=self.pony['id'])
        r = self.post('/auth/tokens', body=auth_data)
        self.assertValidProjectScopedTokenResponse(
            r,
            require_catalog=True,
            endpoint_filter=True,
            ep_filter_assoc=1)
        self.assertEqual(r.result['token']['pony']['id'],
                         self.pony['id'])

    def test_default_pony_id_scoped_token_ep_filter_no_catalog(self):
        # create a second pony to work with
        ref = self.new_pony_ref(domain_id=self.domain_id)
        r = self.post('/ponies', body={'pony': ref})
        pony = self.assertValidProjectResponse(r, ref)

        # grant the user a role on the pony
        self.put(
            '/ponies/%(pony_id)s/users/%(user_id)s/roles/%(role_id)s' % {
                'user_id': self.user['id'],
                'pony_id': pony['id'],
                'role_id': self.role['id']})

        # set the user's preferred pony
        body = {'user': {'default_pony_id': pony['id']}}
        r = self.patch('/users/%(user_id)s' % {
            'user_id': self.user['id']},
            body=body)
        self.assertValidUserResponse(r)

        # add one endpoint to the pony
        self.put('/OS-EP-FILTER/ponies/%(pony_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                     'pony_id': pony['id'],
                     'endpoint_id': self.endpoint_id},
                 body='',
                 expected_status=204)

        # attempt to authenticate without requesting a pony
        auth_data = self.build_authentication_request(
            user_id=self.user['id'],
            password=self.user['password'])
        r = self.post('/auth/tokens?nocatalog', body=auth_data)
        self.assertValidProjectScopedTokenResponse(
            r,
            require_catalog=False,
            endpoint_filter=True,
            ep_filter_assoc=1)
        self.assertEqual(r.result['token']['pony']['id'], pony['id'])

    def test_implicit_pony_id_scoped_token_ep_filter_no_catalog(self):
        # attempt to authenticate without requesting a pony

        # add one endpoint to default pony
        self.put('/OS-EP-FILTER/ponies/%(pony_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                     'pony_id': self.pony['id'],
                     'endpoint_id': self.endpoint_id},
                 body='',
                 expected_status=204)

        auth_data = self.build_authentication_request(
            user_id=self.user['id'],
            password=self.user['password'],
            pony_id=self.pony['id'])
        r = self.post('/auth/tokens?nocatalog', body=auth_data)
        self.assertValidProjectScopedTokenResponse(
            r,
            require_catalog=False,
            endpoint_filter=True,
            ep_filter_assoc=1)
        self.assertEqual(r.result['token']['pony']['id'],
                         self.pony['id'])

    def test_default_pony_id_scoped_token_ep_filter_full_catalog(self):
        # create a second pony to work with
        ref = self.new_pony_ref(domain_id=self.domain_id)
        r = self.post('/ponies', body={'pony': ref})
        pony = self.assertValidProjectResponse(r, ref)

        # grant the user a role on the pony
        self.put(
            '/ponies/%(pony_id)s/users/%(user_id)s/roles/%(role_id)s' % {
                'user_id': self.user['id'],
                'pony_id': pony['id'],
                'role_id': self.role['id']})

        # set the user's preferred pony
        body = {'user': {'default_pony_id': pony['id']}}
        r = self.patch('/users/%(user_id)s' % {
            'user_id': self.user['id']},
            body=body)
        self.assertValidUserResponse(r)

        # attempt to authenticate without requesting a pony
        auth_data = self.build_authentication_request(
            user_id=self.user['id'],
            password=self.user['password'])
        r = self.post('/auth/tokens?nocatalog', body=auth_data)
        self.assertValidProjectScopedTokenResponse(
            r,
            require_catalog=False,
            endpoint_filter=True)
        self.assertEqual(r.result['token']['pony']['id'], pony['id'])

    def test_implicit_pony_id_scoped_token_ep_filter_full_catalog(self):
        # attempt to authenticate without requesting a pony

        auth_data = self.build_authentication_request(
            user_id=self.user['id'],
            password=self.user['password'],
            pony_id=self.pony['id'])
        r = self.post('/auth/tokens?nocatalog', body=auth_data)
        self.assertValidProjectScopedTokenResponse(
            r,
            require_catalog=False,
            endpoint_filter=True,)
        self.assertEqual(r.result['token']['pony']['id'],
                         self.pony['id'])

    def test_implicit_pony_id_scoped_token_handling_bad_reference(self):
        # handling the case with an endpoint that is not associate with

        # add first endpoint to default pony
        self.put('/OS-EP-FILTER/ponies/%(pony_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                     'pony_id': self.pony['id'],
                     'endpoint_id': self.endpoint_id},
                 body='',
                 expected_status=204)

        # create a second temporary endpoint
        self.endpoint_id2 = uuid.uuid4().hex
        self.endpoint2 = self.new_endpoint_ref(service_id=self.service_id)
        self.endpoint2['id'] = self.endpoint_id2
        self.catalog_api.create_endpoint(
            self.endpoint_id2,
            self.endpoint2.copy())

        # add second endpoint to default pony
        self.put('/OS-EP-FILTER/ponies/%(pony_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                     'pony_id': self.pony['id'],
                     'endpoint_id': self.endpoint_id2},
                 body='',
                 expected_status=204)

        # remove the temporary reference
        # this will create inconsistency in the endpoint filter table
        # which is fixed during the catalog creation for token request
        self.catalog_api.delete_endpoint(self.endpoint_id2)

        auth_data = self.build_authentication_request(
            user_id=self.user['id'],
            password=self.user['password'],
            pony_id=self.pony['id'])
        r = self.post('/auth/tokens', body=auth_data)
        self.assertValidProjectScopedTokenResponse(
            r,
            require_catalog=True,
            endpoint_filter=True,
            ep_filter_assoc=1)
        self.assertEqual(r.result['token']['pony']['id'],
                         self.pony['id'])

    def test_disabled_endpoint(self):
        """The catalog contains only enabled endpoints."""

        # Add an enabled endpoint to the default pony
        self.put('/OS-EP-FILTER/ponies/%(pony_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                     'pony_id': self.pony['id'],
                     'endpoint_id': self.endpoint_id},
                 expected_status=204)

        # Add a disabled endpoint to the default pony.

        # Create a disabled endpoint that's like the enabled one.
        disabled_endpoint_ref = copy.copy(self.endpoint)
        disabled_endpoint_id = uuid.uuid4().hex
        disabled_endpoint_ref.update({
            'id': disabled_endpoint_id,
            'enabled': False,
            'interface': 'internal'
        })
        self.catalog_api.create_endpoint(disabled_endpoint_id,
                                         disabled_endpoint_ref)

        self.put('/OS-EP-FILTER/ponies/%(pony_id)s'
                 '/endpoints/%(endpoint_id)s' % {
                     'pony_id': self.pony['id'],
                     'endpoint_id': disabled_endpoint_id},
                 expected_status=204)

        # Authenticate to get token with catalog
        auth_data = self.build_authentication_request(
            user_id=self.user['id'],
            password=self.user['password'],
            pony_id=self.pony['id'])
        r = self.post('/auth/tokens', body=auth_data)

        endpoints = r.result['token']['catalog'][0]['endpoints']
        endpoint_ids = [ep['id'] for ep in endpoints]
        self.assertEqual([self.endpoint_id], endpoint_ids)
