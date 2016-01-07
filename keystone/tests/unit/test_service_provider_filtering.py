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
