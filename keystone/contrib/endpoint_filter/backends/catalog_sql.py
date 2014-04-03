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

import six

from keystone.catalog.backends import sql
from keystone.common import dependency
from keystone import config

CONF = config.CONF


@dependency.requires('endpoint_filter_api')
class EndpointFilterCatalog(sql.Catalog):
    def get_v3_catalog(self, user_id, project_id, metadata=None):
        d = dict(six.iteritems(CONF))
        d.update({'tenant_id': project_id, 'user_id': user_id})
        refs = self.endpoint_filter_api.list_endpoints_for_project(project_id)
        raw_catalog = self.get_raw_catalog()

        d = sql.get_url_data(user_id, project_id)
        if (not refs and
                CONF.endpoint_filter.return_all_endpoints_if_no_filter):
            v3catalog = sql.format_v3_catalog(d, raw_catalog)
            return v3catalog

        #carry over entries from raw that have corresponding entries in refs

        endpoint_id_list = [entry.endpoint_id for entry in refs]
        service_list = []
        for service in raw_catalog:
            endpoint_list = [endpoint
                             for endpoint in service.endpoints
                             if endpoint.id in endpoint_id_list]
        if endpoint_list:
            service.endpoint = endpoint_list
            service_list.append(service)

        v3catalog = sql.format_v3_catalog(d, service_list)

        return v3catalog
