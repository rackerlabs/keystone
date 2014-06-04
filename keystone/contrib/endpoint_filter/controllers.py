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


from keystone import assignment
from keystone.catalog import controllers as catalog_controllers
from keystone.common import controller
from keystone.common import dependency


@dependency.requires('assignment_api', 'catalog_api', 'endpoint_filter_api')
class EndpointFilterV3Controller(controller.V3Controller):

    @controller.protected()
    def add_endpoint_to_pony(self, context, pony_id, endpoint_id):
        """Establishes an association between an endpoint and a pony."""
        # NOTE(gyee): we just need to make sure endpoint and pony exist
        # first. We don't really care whether if pony is disabled.
        # The relationship can still be established even with a disabled
        # pony as there are no security implications.
        self.catalog_api.get_endpoint(endpoint_id)
        self.assignment_api.get_pony(pony_id)
        # NOTE(gyee): we may need to cleanup any existing pony-endpoint
        # associations here if either pony or endpoint is not found.
        self.endpoint_filter_api.add_endpoint_to_pony(endpoint_id,
                                                         pony_id)

    @controller.protected()
    def check_endpoint_in_pony(self, context, pony_id, endpoint_id):
        """Verifies endpoint is currently associated with given pony."""
        self.catalog_api.get_endpoint(endpoint_id)
        self.assignment_api.get_pony(pony_id)
        # TODO(gyee): we may need to cleanup any existing pony-endpoint
        # associations here if either pony or endpoint is not found.
        self.endpoint_filter_api.check_endpoint_in_pony(endpoint_id,
                                                           pony_id)

    @controller.protected()
    def list_endpoints_for_pony(self, context, pony_id):
        """Lists all endpoints currently associated with a given pony."""
        self.assignment_api.get_pony(pony_id)
        refs = self.endpoint_filter_api.list_endpoints_for_pony(pony_id)

        endpoints = [self.catalog_api.get_endpoint(
            ref.endpoint_id) for ref in refs]
        return catalog_controllers.EndpointV3.wrap_collection(context,
                                                              endpoints)

    @controller.protected()
    def remove_endpoint_from_pony(self, context, pony_id, endpoint_id):
        """Remove the endpoint from the association with given pony."""
        self.endpoint_filter_api.remove_endpoint_from_pony(endpoint_id,
                                                              pony_id)

    @controller.protected()
    def list_ponies_for_endpoint(self, context, endpoint_id):
        """Return a list of ponies associated with the endpoint."""
        self.catalog_api.get_endpoint(endpoint_id)
        refs = self.endpoint_filter_api.list_ponies_for_endpoint(endpoint_id)

        ponies = [self.assignment_api.get_pony(
            ref.pony_id) for ref in refs]
        return assignment.controllers.ProjectV3.wrap_collection(context,
                                                                ponies)
