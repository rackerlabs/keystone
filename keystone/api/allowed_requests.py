#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

# This file handles all flask-restful resources for /v3/allowed-requests

from keystone.common import provider_api
from keystone.server import flask as ks_flask


PROVIDERS = provider_api.ProviderAPIs


class AllowedRequestResource(ks_flask.ResourceBase):
    collection_key = 'allowed_requests'
    member_key = 'allowed_request'
    get_member_from_driver = PROVIDERS.deferred_provider_lookup(
        api='allowed_request_api', method='get_allowed_request')

    def get(self, allowed_request_id=None):
        """Get an allowed request format or list all allowed request formats.

        GET/HEAD /v3/allowed-requests
        GET/HEAD /v3/allowed-requests/{allowed_request_id}
        """
        if allowed_request_id is not None:
            return self._get_allowed_request(allowed_request_id)
        return self._list_allowed_requests()

    def _get_allowed_request(self, allowed_request_id):
        # NOTE(cmurphy): Deliberately unenforced
        allowed_request = (
            PROVIDERS.allowed_request_api.get_allowed_request(allowed_request_id)
        )
        return self.wrap_member(allowed_request)

    def _list_allowed_requests(self):
        # NOTE(cmurphy): Deliberately unenforced
        refs = PROVIDERS.allowed_requests_api.list_allowed_requests()
        return self.wrap_collection(refs)


class AllowedRequestAPI(ks_flask.APIBase):
    _name = 'allowed_request'
    _import_name = __name__
    resources = [AllowedRequestResource]


APIs = (AllowedRequestAPI,)
