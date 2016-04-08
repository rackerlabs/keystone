# Copyright 2016 Red Hat, Inc.
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

from keystone_tempest_plugin.services.identity import base_clients

from oslo_serialization import jsonutils

from tempest.lib.common import rest_client


class ServiceProvidersClient(base_clients.FederationClient):

    api_name = 'service_providers'

    def create_service_provider(self, sp_id, **kwargs):
        """Creates an service provider."""
        put_body = jsonutils.dumps({'service_provider': kwargs})
        resp, body = self.put(sp_id, put_body)
        self.expected_success(201, resp.status)
        body = jsonutils.loads(body)
        sp = rest_client.ResponseBody(resp, body)['service_provider']
        self.test_case.addCleanup(self.delete_service_provider, sp['id'])
        return sp

    def list_service_providers(self):
        """Lists the service providers."""
        resp, body = self.get()
        self.expected_success(200, resp.status)
        body = jsonutils.loads(body)
        return rest_client.ResponseBody(resp, body)['service_providers']

    def show_service_provider(self, sp_id):
        """Gets an service provider."""
        resp, body = self.get(sp_id)
        self.expected_success(200, resp.status)
        body = jsonutils.loads(body)
        return rest_client.ResponseBody(resp, body)['service_provider']

    def delete_service_provider(self, sp_id):
        """Deletes an service provider."""
        resp, body = self.delete(sp_id)
        self.expected_success(204, resp.status)
        return rest_client.ResponseBody(resp, body)

    def update_service_provider(self, sp_id, **kwargs):
        """Updates an service provider."""
        patch_body = jsonutils.dumps({'service_provider': kwargs})
        resp, body = self.patch(sp_id, patch_body)
        self.expected_success(200, resp.status)
        body = jsonutils.loads(body)
        return rest_client.ResponseBody(resp, body)['service_provider']

    def get_service_providers_in_token(self):
        """Gets the service providers list present in the token.

        Only enabled servie providers are displayed in the token.
        """
        # First we force the auth_data update
        self.auth_provider.set_auth()

        # Now we can retrieve the updated auth_data
        auth_data = self.auth_provider.get_auth()[1]
        try:
            return auth_data['service_providers']
        except KeyError:
            # no service providers in token
            pass
        return []
