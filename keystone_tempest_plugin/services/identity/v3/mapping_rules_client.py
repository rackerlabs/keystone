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


class MappingRulesClient(base_clients.FederationClient):

    api_name = 'mappings'

    def create_mapping_rule(self, mapping_id, rules):
        """Create an mapping rule."""
        put_body = jsonutils.dumps({'mapping': rules})
        resp, body = self._put(mapping_id, put_body)
        self.expected_success(201, resp.status)
        body = jsonutils.loads(body)
        sp = rest_client.ResponseBody(resp, body)['mapping']
        return sp

    def list_mapping_rules(self):
        """List the mapping rules."""
        resp, body = self._get()
        self.expected_success(200, resp.status)
        body = jsonutils.loads(body)
        return rest_client.ResponseBody(resp, body)['mappings']

    def show_mapping_rule(self, mapping_id):
        """Get an mapping rule."""
        resp, body = self._get(mapping_id)
        self.expected_success(200, resp.status)
        body = jsonutils.loads(body)
        return rest_client.ResponseBody(resp, body)['mapping']

    def delete_mapping_rule(self, mapping_id):
        """Delete an mapping rule."""
        resp, body = self._delete(mapping_id)
        self.expected_success(204, resp.status)
        return rest_client.ResponseBody(resp, body)

    def update_mapping_rule(self, mapping_id, rules):
        """Update an mapping rule."""
        patch_body = jsonutils.dumps({'mapping': rules})
        resp, body = self._patch(mapping_id, patch_body)
        self.expected_success(200, resp.status)
        body = jsonutils.loads(body)
        return rest_client.ResponseBody(resp, body)['mapping']
