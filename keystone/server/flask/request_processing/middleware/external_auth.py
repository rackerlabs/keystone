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

from keystonemiddleware import external_oauth2_token

from keystone.common import context


class ExternalOAuth2Context(external_oauth2_token.ExternalAuth2Protocol):
    def __init__(self, app):
        super().__init__(app, {})

    def process_request(self, request):
        response = super().process_request(request)
        if response:
            return response

        request_context = context.RequestContext.from_environ(
            request.environ, authenticated=True, overwrite=True
        )
        request.environ[context.REQUEST_CONTEXT_ENV] = request_context
