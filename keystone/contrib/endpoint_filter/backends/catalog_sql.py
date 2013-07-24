from keystone.catalog.backends import sql
from keystone.catalog import core as catalog_core
from keystone import config
from keystone.contrib.endpoint_filter import core as ep_filter

CONF = config.CONF


class OS_EP_Filter_Catalog(sql.Catalog):
    def get_v3_catalog(self, user_id, tenant_id, metadata=None):
        d = dict(CONF.iteritems())
        d.update({'tenant_id': tenant_id, 'user_id': user_id})

        services = {}

        ep_filter_api = ep_filter.Manager()
        refs = ep_filter_api.list_endpoints_in_project(tenant_id)
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
