from keystone import catalog


''' Default discovery service using the existing service catalog.
    Should be replaced once virtual IdP management is available'''
class Default(object):


    def __init__(self):
        ''' Constructor '''
        self.catalog_api = catalog.controllers.ServiceV3()
        self.endpoint_api = catalog.controllers.EndpointV3()

    def get_directory(self):
        ''' Return services which match idp.* from the service catalog '''
        return self.format_directory(self.catalog_api.list_services({"is_admin":True, "query_string":{}, "path":"/"}))

    def populate_auth_dict(self, federated, provider):
        ''' Populate the given federated dict with validation and endpoint data
            for the specified provider'''
        endpoints = self.endpoint_api.list_endpoints({"is_admin":True, "query_string":{}, "path":"/"})
        service = self.catalog_api.get_service({"is_admin":True}, provider)["service"]
        for endpoint in endpoints["endpoints"]:
            if not endpoint["interface"]=="public":
                endpoints["endpoints"].pop(endpoints["endpoints"].index(endpoint))
            elif endpoint["service_id"]==service["id"]:
                validation = endpoint.get("validation", None)
                federated["validation"] = validation
                endpoint_url = endpoint["url"]
                federated["endpoint"] = endpoint_url
        federated["protocol"] = service["type"].split(".")[1]
 
    def format_directory(self, services):
        ''' Format the list of services to exclude non-identity-provider services'''
        providers = []
        endpoints = self.endpoint_api.list_endpoints({"is_admin":True, "query_string":{}, "path":"/"})
        for service in services["services"]:
            if service["type"].startswith("idp"):
                for endpoint in endpoints["endpoints"]:
                    if not endpoint["interface"]=="public":
                        endpoints["endpoints"].pop(endpoints["endpoints"].index(endpoint))
                    elif endpoint["service_id"]==service["id"]:
                        providers.append(service)
        return {"providers": providers}
