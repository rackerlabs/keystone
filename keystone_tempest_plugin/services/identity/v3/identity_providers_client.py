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


class IdentityProvidersClient(base_clients.FederationClient):

    api_name = 'identity_providers'

    def create_identity_provider(self, idp_id, **kwargs):
        """Creates an identity provider."""
        put_body = jsonutils.dumps({'identity_provider': kwargs})
        resp, body = self.put(idp_id, put_body)
        self.expected_success(201, resp.status)
        body = jsonutils.loads(body)
        idp = rest_client.ResponseBody(resp, body)['identity_provider']
        self.test_case.addCleanup(self.delete_identity_provider, idp['id'])
        return idp

    def list_identity_providers(self):
        """Lists the identity providers."""
        resp, body = self.get()
        self.expected_success(200, resp.status)
        body = jsonutils.loads(body)
        return rest_client.ResponseBody(resp, body)['identity_providers']

    def show_identity_provider(self, idp_id):
        """Gets an identity provider."""
        resp, body = self.get(idp_id)
        self.expected_success(200, resp.status)
        body = jsonutils.loads(body)
        return rest_client.ResponseBody(resp, body)['identity_provider']

    def delete_identity_provider(self, idp_id):
        """Deletes an identity provider."""
        resp, body = self.delete(idp_id)
        self.expected_success(204, resp.status)
        return rest_client.ResponseBody(resp, body)

    def update_identity_provider(self, idp_id, **kwargs):
        """Updates an identity provider."""
        patch_body = jsonutils.dumps({'identity_provider': kwargs})
        resp, body = self.patch(idp_id, patch_body)
        self.expected_success(200, resp.status)
        body = jsonutils.loads(body)
        return rest_client.ResponseBody(resp, body)['identity_provider']
