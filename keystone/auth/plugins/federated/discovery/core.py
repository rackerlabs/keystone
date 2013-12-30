# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

from keystone import catalog

'''Default discovery service using the existing service catalog.
   Should be replaced once virtual IdP management is available
'''


class Default(object):

    def __init__(self):
        '''Constructor.'''
        self.catalog_api = catalog.controllers.ServiceV3()
        self.endpoint_api = catalog.controllers.EndpointV3()

    def get_directory(self):
        '''Return services which match idp.*
           from the service catalog.
        '''
        return self.format_directory(
            self.catalog_api.list_services(
                {"is_admin": True, "query_string": {}, "path": "/"}))

    def populate_auth_dict(self, federated, provider):
        '''Populate the given federated dict with validation
           and endpoint data for the specified provider.
        '''
        endpoints = self.endpoint_api.list_endpoints(
            {"is_admin": True, "query_string": {}, "path": "/"})
        service = self.catalog_api.get_service(
            {"is_admin": True}, provider)["service"]
        for endpoint in endpoints["endpoints"]:
            if not endpoint["interface"] == "public":
                endpoints["endpoints"].pop(
                    endpoints["endpoints"].index(endpoint))
            elif endpoint["service_id"] == service["id"]:
                validation = endpoint.get("validation", None)
                federated["validation"] = validation
                endpoint_url = endpoint["url"]
                federated["endpoint"] = endpoint_url
        federated["protocol"] = service["type"].split(".")[1]

    def format_directory(self, services):
        '''Format the list of services to exclude
           non-identity-provider services.
        '''
        providers = []
        endpoints = self.endpoint_api.list_endpoints(
            {"is_admin": True, "query_string": {}, "path": "/"})
        for service in services["services"]:
            if service["type"].startswith("idp"):
                for endpoint in endpoints["endpoints"]:
                    if not endpoint["interface"] == "public":
                        endpoints["endpoints"].pop(
                            endpoints["endpoints"].index(endpoint))
                    elif endpoint["service_id"] == service["id"]:
                        providers.append(service)
        return {"providers": providers}
