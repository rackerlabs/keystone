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
        """Create an service provider.

        :param str sp_id: The ID to be used to create the Service Provider.
        :param kwargs: Extra attributes. Mandatory: auth_url (str) and sp_url
                       (str). Optional: description (str), enabled (boolean)
                       and relay_state_prefix (str).
        """
        put_body = jsonutils.dumps({'service_provider': kwargs})
        resp, body = self._put(sp_id, put_body)
        self.expected_success(201, resp.status)
        body = jsonutils.loads(body)
        sp = rest_client.ResponseBody(resp, body)['service_provider']
        return sp

    def list_service_providers(self):
        """List the service providers."""
        resp, body = self._get()
        self.expected_success(200, resp.status)
        body = jsonutils.loads(body)
        return rest_client.ResponseBody(resp, body)['service_providers']

    def show_service_provider(self, sp_id):
        """Get an service provider."""
        resp, body = self._get(sp_id)
        self.expected_success(200, resp.status)
        body = jsonutils.loads(body)
        return rest_client.ResponseBody(resp, body)['service_provider']

    def delete_service_provider(self, sp_id):
        """Delete an service provider."""
        resp, body = self._delete(sp_id)
        self.expected_success(204, resp.status)
        return rest_client.ResponseBody(resp, body)

    def update_service_provider(self, sp_id, **kwargs):
        """Update an service provider.

        :param str sp_id: The ID of the Service Provider to be updated.
        :param kwargs: All attributes to be updated: auth_url (str) and sp_url
                       (str), description (str), enabled (boolean) and
                       relay_state_prefix (str).
        """
        patch_body = jsonutils.dumps({'service_provider': kwargs})
        resp, body = self._patch(sp_id, patch_body)
        self.expected_success(200, resp.status)
        body = jsonutils.loads(body)
        return rest_client.ResponseBody(resp, body)['service_provider']

    def get_service_providers_in_token(self):
        """Get the service providers list present in the token.

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
            return []
