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

import uuid

from oslo_config import cfg
from six.moves import http_client

from keystone.tests.unit import test_v3


CONF = cfg.CONF


class EndpointFilterTestCase(test_v3.RestfulTestCase):

    def config_overrides(self):
        super(EndpointFilterTestCase, self).config_overrides()
        self.config_fixture.config(
            group='catalog', driver='endpoint_filter.sql')


class ServiceProviderProjectAssociationTestCase(EndpointFilterTestCase):

    SERVICE_PROVIDER_ID = 'ACME'
    SP_AUTH_URL = ('http://beta.com:5000/v3/OS-FEDERATION/identity_providers'
                   '/BETA/protocols/saml2/auth')

    def setUp(self):
        super(EndpointFilterTestCase, self).setUp()
        self.default_request_url = (
            '/OS-EP-FILTER/projects/%(project_id)s'
            '/service_providers/%(sp_id)s' % {
                'project_id': self.default_domain_project_id,
                'sp_id': self.SERVICE_PROVIDER_ID})

        service_provider = {
            'auth_url': self.SP_AUTH_URL,
            'enabled': True,
            'description': uuid.uuid4().hex,
            'sp_url': self.SP_AUTH_URL,
            'relay_state_prefix': CONF.saml.relay_state_prefix
        }

        url = '/OS-FEDERATION/service_providers/' + self.SERVICE_PROVIDER_ID
        self.put(url, body={'service_provider': service_provider},
                 expected_status=http_client.CREATED)

    def test_create_project_sp_association(self):
        """PUT /OS-EP-FILTER/projects/{project_id}
               /service_providers/{service_provider_id}

        Valid endpoint and project id test case.

        """
        self.put(self.default_request_url)

    def test_create_endpoint_project_association_with_invalid_project(self):
        """PUT /OS-EP-FILTER/projects/{project_id}
               /service_providers/{service_provider_id}

        Invalid project id test case.

        """
        self.put('/OS-EP-FILTER/projects/%(project_id)s'
                 '/service_providers/%(service_provider_id)s' % {
                     'project_id': uuid.uuid4().hex,
                     'service_provider_id': self.SERVICE_PROVIDER_ID},
                 expected_status=http_client.NOT_FOUND)

    def test_create_endpoint_project_association_with_invalid_sp(self):
        """PUT /OS-EP-FILTER/projects/{project_id}
               /service_providers/{service_provider_id}

        Invalid endpoint id test case.

        """
        self.put('/OS-EP-FILTER/projects/%(project_id)s'
                 '/service_providers/%(service_provider_id)s' % {
                     'project_id': self.default_domain_project_id,
                     'service_provider_id': uuid.uuid4().hex},
                 expected_status=http_client.NOT_FOUND)

    def test_create_endpoint_project_association_with_unexpected_body(self):
        """PUT /OS-EP-FILTER/projects/{project_id}
               /service_providers/{service_provider_id}

        Unexpected body in request. The body should be ignored.

        """
        self.put(self.default_request_url,
                 body={'project_id': self.default_domain_project_id})

    def test_check_endpoint_project_association(self):
        """HEAD /OS-EP-FILTER/projects/{project_id}
                /service_providers/{service_provider_id}

        Valid project and endpoint id test case.

        """
        self.put(self.default_request_url)
        self.head('/OS-EP-FILTER/projects/%(project_id)s'
                  '/service_providers/%(service_provider_id)s' % {
                      'project_id': self.default_domain_project_id,
                      'service_provider_id': self.SERVICE_PROVIDER_ID})

    def test_check_nonexisting_service_provider_association(self):
        """HEAD /OS-EP-FILTER/projects/{project_id}
                /service_providers/{service_provider_id}

        Expect HTTP 404 while checking nonexisting association

        """
        self.head('/OS-EP-FILTER/projects/%(project_id)s'
                  '/service_providers/%(service_provider_id)s' % {
                      'project_id': self.default_domain_project_id,
                      'service_provider_id': self.SERVICE_PROVIDER_ID},
                  expected_status=http_client.NOT_FOUND)

    def test_check_endpoint_project_association_with_invalid_project(self):
        """HEAD /OS-EP-FILTER/projects/{project_id}
                /service_providers/{service_provider_id}

        Invalid project id test case.

        """
        self.put(self.default_request_url)
        self.head('/OS-EP-FILTER/projects/%(project_id)s'
                  '/service_providers/%(service_provider_id)s' % {
                      'project_id': uuid.uuid4().hex,
                      'service_provider_id': self.SERVICE_PROVIDER_ID},
                  expected_status=http_client.NOT_FOUND)

    def test_check_endpoint_project_association_with_invalid_endpoint(self):
        """HEAD /OS-EP-FILTER/projects/{project_id}
                /service_providers/{service_provider_id}

        Invalid endpoint id test case.

        """
        self.put(self.default_request_url)
        self.head('/OS-EP-FILTER/projects/%(project_id)s'
                  '/service_providers/%(service_provider_id)s' % {
                      'project_id': self.default_domain_project_id,
                      'service_provider_id': uuid.uuid4().hex},
                  expected_status=http_client.NOT_FOUND)

    def test_delete_project_service_provider_association(self):

        self.put(self.default_request_url)
        self.head(self.default_request_url)

        self.delete(self.default_request_url)
        self.head(self.default_request_url,
                  expected_status=http_client.NOT_FOUND)

    def test_list_service_providers_associated_with_valid_project(self):
        """GET /OS-EP-FILTER/projects/{project_id}/service_providers

        Valid project and endpoint id test case.

        """
        self.put(self.default_request_url)
        resource_url = ('/OS-EP-FILTER/projects/%(project_id)s'
                        '/service_providers' % {
                            'project_id': self.default_domain_project_id})
        resp = self.get(resource_url)
        self.assertValidServiceProviderListResponse(resp)

    def test_list_service_providers_associated_with_invalid_project(self):
        """GET /OS-EP-FILTER/projects/{project_id}/service_providers

        Invalid project id test case.

        """
        self.put(self.default_request_url)
        self.get('/OS-EP-FILTER/projects/%(project_id)s/service_providers' % {
                 'project_id': uuid.uuid4().hex},
                 expected_status=http_client.NOT_FOUND)

    def test_list_projects_associated_with_service_provider(self):
        """GET /OS-EP-FILTER/service_providers/{service_provider_id}/projects

        Valid endpoint-project association test case.

        """
        self.put(self.default_request_url)
        resource_url = ('/OS-EP-FILTER/service_providers'
                        '/%(service_provider_id)s/projects' % {
                            'service_provider_id': self.SERVICE_PROVIDER_ID})
        self.get(resource_url)

    def test_list_projects_with_no_service_provider_association(self):
        """GET /OS-EP-FILTER/service_providers/{service_provider_id}/projects

        Valid service_provider id but no service_provider-project associations
        test case.

        """
        r = self.get('/OS-EP-FILTER/service_providers'
                     '/%(service_provider_id)s/projects' %
                     {'service_provider_id': self.SERVICE_PROVIDER_ID})
        self.assertValidProjectListResponse(r, expected_length=0)

    def test_list_projects_associated_with_invalid_service_provider(self):
        """GET /OS-EP-FILTER/service_providers/{service_provider_id}/projects

        Invalid service_provider id test case.

        """
        self.get('/OS-EP-FILTER/service_providers'
                 '/%(service_provider_id)s/projects' %
                 {'service_provider_id': uuid.uuid4().hex},
                 expected_status=http_client.NOT_FOUND)

    def test_remove_service_provider_project_association(self):
        """DELETE /OS-EP-FILTER/projects/{project_id}'
                  '/service_providers/{service_provider_id}

        Valid project id and service_provider id test case.

        """
        self.put(self.default_request_url)
        self.delete('/OS-EP-FILTER/projects/%(project_id)s'
                    '/service_providers/%(service_provider_id)s' % {
                        'project_id': self.default_domain_project_id,
                        'service_provider_id': self.SERVICE_PROVIDER_ID})

    def test_remove_service_provider_project_association_invalid_project(self):
        """DELETE /OS-EP-FILTER/projects/{project_id}
                  /service_providers/{service_provider_id}

        Invalid project id test case.

        """
        self.put(self.default_request_url)
        self.delete('/OS-EP-FILTER/projects/%(project_id)s'
                    '/service_providers/%(service_provider_id)s' % {
                        'project_id': uuid.uuid4().hex,
                        'service_provider_id': self.SERVICE_PROVIDER_ID},
                    expected_status=http_client.NOT_FOUND)

    def test_remove_service_provider_project_association_invalid_sp(self):
        """DELETE /OS-EP-FILTER/projects/{project_id}
                  /service_providers/{service_provider_id}

        Invalid service_provider id test case.

        """
        self.put(self.default_request_url)
        self.delete('/OS-EP-FILTER/projects/%(project_id)s'
                    '/service_providers/%(service_provider_id)s' % {
                        'project_id': self.default_domain_project_id,
                        'service_provider_id': uuid.uuid4().hex},
                    expected_status=http_client.NOT_FOUND)

    def test_sp_project_association_cleanup_when_project_deleted(self):
        self.put(self.default_request_url)
        association_url = ('/OS-EP-FILTER/service_providers'
                           '/%(service_provider_id)s/projects' %
                           {'service_provider_id': self.SERVICE_PROVIDER_ID})
        r = self.get(association_url)

        # expect one project to be returned in the response body
        self.assertEqual(1, len(r.result.get('projects')))

        self.delete('/projects/%(project_id)s' % {
            'project_id': self.default_domain_project_id})

        r = self.get(association_url)
        # expect no projects to be returned in the response body
        self.assertEqual(0, len(r.result.get('projects')))

    def test_sp_project_association_cleanup_when_endpoint_deleted(self):
        self.put(self.default_request_url)
        association_url = ('/OS-EP-FILTER/projects/%(project_id)s/'
                           'service_providers' % {
                               'project_id': self.default_domain_project_id})
        r = self.get(association_url)
        self.assertEqual(1, len(r.result.get('service_providers')))

        self.delete(('/OS-FEDERATION/service_providers'
                     '/%(service_provider_id)s' % {
                         'service_provider_id': self.SERVICE_PROVIDER_ID}))

        r = self.get(association_url)
        self.assertEqual(0, len(r.result.get('service_providers')))


class ServiceProvidersGroupTestCase(EndpointFilterTestCase):
    SERVICE_PROVIDER_ID = 'ACME'
    SP_AUTH_URL = ('http://beta.com:5000/v3/OS-FEDERATION/identity_providers'
                   '/BETA/protocols/saml2/auth')

    def setUp(self):
        super(EndpointFilterTestCase, self).setUp()

        service_provider = {
            'auth_url': self.SP_AUTH_URL,
            'enabled': True,
            'description': uuid.uuid4().hex,
            'sp_url': self.SP_AUTH_URL,
            'relay_state_prefix': CONF.saml.relay_state_prefix
        }

        url = '/OS-FEDERATION/service_providers/' + self.SERVICE_PROVIDER_ID
        self.put(url, body={'service_provider': service_provider},
                 expected_status=http_client.CREATED)

    def assertServiceProvidersGroup(self, sp, ref=None):
        for attr in ['id', 'name', 'description',
                     'service_providers', 'links']:
            self.assertIsNotNone(sp.get(attr))

            if ref:
                for attr in ['name', 'description']:
                    self.assertEqual(ref.get(attr), sp.get(attr))

                # compare service providers, for that use sets to overcome
                # ordering differences
                self.assertEqual(set(ref.get('service_providers', [])),
                                 set(sp.get('service_providers', [])))

    def new_sp_group(self, service_providers=None):
        ref = {
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex,
            'description': uuid.uuid4().hex,
        }

        if service_providers:
            ref['service_providers'] = service_providers
        else:
            ref['service_providers'] = [self.SERVICE_PROVIDER_ID]

        return ref

    def test_create_service_providers_group(self):
        """Test simple creating of the service providers group."""
        sp_group = self.new_sp_group()
        self.post('/OS-EP-FILTER/service_providers_groups',
                  body={'service_providers_group': sp_group})

    # FIXME(marek-denis): This test should not pass as we have a non existing
    # service provider in the filters list.
    def test_create_service_providers_group_nonexisting_sp(self):
        sp_group = self.new_sp_group()
        sp_group['service_providers'].append(uuid.uuid4().hex)
        r = self.post('/OS-EP-FILTER/service_providers_groups',
                      body={'service_providers_group': sp_group})
        sp_group_id = r.result['service_providers_group']['id']
        r = self.get('/OS-EP-FILTER/service_providers_groups/' + sp_group_id)

    def test_get_service_providers_group(self):
        """Test fetching existing service providers group.

        Test scenario:
        1) Add a service providers group.
        2) Get a service providers group

        """
        sp_group_ref = self.new_sp_group()
        sp_group = self.post('/OS-EP-FILTER/service_providers_groups',
                             body={'service_providers_group': sp_group_ref})
        self.assertServiceProvidersGroup(
            sp_group.result['service_providers_group'], ref=sp_group_ref)
        sp_group_id = sp_group.result['service_providers_group']['id']
        sp_group = self.get(
            '/OS-EP-FILTER/service_providers_groups/' + sp_group_id)
        self.assertServiceProvidersGroup(
            sp_group.result['service_providers_group'], ref=sp_group_ref)

    def test_get_nonexisting_service_providers_group(self):
        """Test fetching existing service providers group that does not exist.

        Test scenario:
        1) Get a service providers group
        2) Expect HTTP 404 return code
        """
        sp_group_id = uuid.uuid4().hex
        self.get('/OS-EP-FILTER/service_providers_groups/' + sp_group_id,
                 expected_status=http_client.NOT_FOUND)

    def test_head_service_providers_group(self):
        """Test HEAD request on existing service providers group."""
        sp_group = self.new_sp_group()
        sp_group = self.post('/OS-EP-FILTER/service_providers_groups',
                             body={'service_providers_group': sp_group})

        sp_group_id = sp_group.result['service_providers_group']['id']
        self.head('/OS-EP-FILTER/service_providers_groups/' + sp_group_id)

    def test_head_nonexisting_service_providers_group(self):
        """Test HEAD request on non existing service providers group.

        Test scenario:
        1) Requset HTTP HEAD on non existing service providers group
        2) Expect server to resonse with 404 code

        """
        sp_group_id = uuid.uuid4().hex
        self.head('/OS-EP-FILTER/service_providers_groups/' + sp_group_id,
                  expected_status=http_client.NOT_FOUND)

    def test_update_service_providers_group(self):
        """Test updating of service provders group

        First and foremost this tests excercises adding and updating list of
        affiliated service providers. It checks whether adding service
        providers as well as removing service providers is correctly reflected
        in the server.

        Test scenario:
        1) Add a standard service providers group
        2) Get service providers group and ensure the sent and received objects
           are equal
        3) Add 3 more service providers to the service providers group objects
           (with random names)
        4) Update object, fetch and compare
        5) Remove first service provider from the service providers' list of
        service providers group object and update server
        6) Fetch object and compare values

        """
        sp_group_ref = self.new_sp_group()

        sp_group = self.post('/OS-EP-FILTER/service_providers_groups',
                             body={'service_providers_group': sp_group_ref})

        sp_group_id = sp_group.result['service_providers_group']['id']
        url = '/OS-EP-FILTER/service_providers_groups/' + sp_group_id
        sp_group = self.get(url)

        self.assertServiceProvidersGroup(
            sp_group.result['service_providers_group'], ref=sp_group_ref)

        sp_group_ref['service_providers'].append(uuid.uuid4().hex)
        sp_group_ref['service_providers'].append(uuid.uuid4().hex)
        sp_group_ref['service_providers'].append(uuid.uuid4().hex)

        self.patch(url, body={'service_providers_group': sp_group_ref})
        sp_group = self.get(url)
        self.assertServiceProvidersGroup(
            sp_group.result['service_providers_group'], ref=sp_group_ref)

        # Remove first element, which is 'ACME' in this case
        sp_group_ref['service_providers'].pop(0)
        self.patch(url, body={'service_providers_group': sp_group_ref})
        sp_group = self.get(url)
        self.assertServiceProvidersGroup(
            sp_group.result['service_providers_group'], ref=sp_group_ref)

    def update_nonexisting_providers_group(self):
        pass

    def test_delete_service_providers_group(self):
        """Delete existing service providers group.

        Ensure that there is nothing left after the operation.
        Test scenario:
        1) Add a service providers group
        2) Ensure it's added correctly (fetch and check HTTP status code)
        3) Delete service providesr group
        4) Try fetching sevicep providers group, expect HTTP 404 return code

        """
        sp_group = self.new_sp_group()
        sp_group = self.post('/OS-EP-FILTER/service_providers_groups',
                             body={'service_providers_group': sp_group})
        sp_group_id = sp_group.result['service_providers_group']['id']
        self.get('/OS-EP-FILTER/service_providers_groups/' + sp_group_id)

        self.delete('/OS-EP-FILTER/service_providers_groups/' + sp_group_id)
        self.get('/OS-EP-FILTER/service_providers_groups/' + sp_group_id,
                 expected_status=http_client.NOT_FOUND)

    def test_list_service_providers_groups(self):
        sp_groups_ref = [self.new_sp_group(),
                         self.new_sp_group(),
                         self.new_sp_group()]
        for sp_group in sp_groups_ref:
            self.post('/OS-EP-FILTER/service_providers_groups',
                      body={'service_providers_group': sp_group})
        sp_groups = self.get('/OS-EP-FILTER/service_providers_groups')
        self.assertEqual(len(sp_groups_ref),
                         len(sp_groups.result['service_providers_groups']))
