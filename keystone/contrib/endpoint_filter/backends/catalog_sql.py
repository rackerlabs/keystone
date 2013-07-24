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

from keystone.catalog.backends import sql
from keystone.catalog import core as catalog_core
from keystone.common import dependency
from keystone import config

CONF = config.CONF


@dependency.requires('endpoint_filter_api')
class Endpoint_Filter_Catalog(sql.Catalog):
    def get_v3_catalog(self, user_id, tenant_id, metadata=None):
        d = dict(CONF.iteritems())
        d.update({'tenant_id': tenant_id, 'user_id': user_id})

        services = {}

        refs = self.endpoint_filter_api.list_endpoints_in_project(tenant_id)
        endpoints = [self.get_endpoint(x.endpoint_id) for x in refs]

        for endpoint in endpoints:
            # look up the service
            service_id = endpoint['service_id']
            services.setdefault(
                service_id,
                self.get_service(service_id))
            service = services[service_id]
            del endpoint['service_id']
            endpoint['url'] = catalog_core.format_url(
                endpoint['url'], d)
            #populate filtered endpoints
            if 'endpoints' in services[service_id]:
                services[service_id]['endpoints'].append(endpoint)
            else:
                services[service_id]['endpoints'] = [endpoint]

        # format catalog
        catalog = []
        for service_id, service in services.iteritems():
            formatted_service = {}
            formatted_service['id'] = service['id']
            formatted_service['type'] = service['type']
            formatted_service['endpoints'] = service['endpoints']
            catalog.append(formatted_service)

        return catalog
