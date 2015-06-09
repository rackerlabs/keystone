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


class Formatter(object):

    @classmethod
    def get_token_data_v2(self, access_token):

        token = {}
        token_data = {}
        access = {}

        token['expires'] = access_token.expires_at
        token['issued_at'] = access_token.issued_at

        user = {}

        user['id'] = access_token.user.id
        user['name'] = access_token.user.name

        access['user'] = user

        if hasattr(access_token, 'project'):
            project = {}
            project['id'] = access_token.project.id
            project['name'] = access_token.project.name

            token['tenant'] = project

        if hasattr(access_token, 'trust'):
            trust = {}
            trust['id'] = access_token.trust.id
            trust['impersonation'] = access_token.trust.impersonation
            trust['trustor_user_id'] = access_token.trust.trustor_user
            trust['trustee_user_id'] = access_token.trust.trustee_user

            access['OS-TRUST:trust'] = trust

        roles = []

        for role in access_token.roles:
            role_info = {}
            role_info['id'] = role.id
            role_info['name'] = role.name
            roles.append(role_info)

        access['user']['roles'] = roles

        if access_token.catalog:
            catalog = []

            for service in access_token.catalog:
                service_info = {}
                service_info['type'] = service.type
                service_info['name'] = service.name

                endpoints = []

                for endpoint in service.endpoints:
                    endpoint_info = {}
                    endpoint_info['id'] = endpoint.id
                    # TODO(dhu) needs endpoint tenantId once Access
                    # info implements it
                    endpoint_info['region'] = endpoint.region
                    if hasattr(endpoint, 'interface'):
                        endpoint_info['type'] = endpoint.interface
                    if hasattr(endpoint, 'publicURL'):
                        endpoint_info['publicURL'] = endpoint.publicURL
                    if hasattr(endpoint, 'internalURL'):
                        endpoint_info['internalURL'] = endpoint.internalURL
                    if hasattr(endpoint, 'adminURL'):
                        endpoint_info['adminURL'] = endpoint.adminURL
                    if hasattr(endpoint, 'versionInfo'):
                        endpoint_info['versionInfo'] = endpoint.versionInfo
                    if hasattr(endpoint, 'versionList'):
                        endpoint_info['versionList'] = endpoint.versionList
                    if hasattr(endpoint, 'versionId'):
                        endpoint_info['versionId'] = endpoint.versionId
                    endpoints.append(endpoint_info)

                service_info['endpoints'] = endpoints
                catalog.append(service_info)

            access['catalog'] = catalog

        token_data['access'] = access
        token_data['access']['token'] = token

        return token_data

    @classmethod
    def get_token_data_v3(self, access_token):
        token = {}
        token_data = {}

        token['expires_at'] = access_token.expires_at
        token['issued_at'] = access_token.issued_at

        # Can the method which is a list be assigned as follow?

        methods = []

        for method in access_token.methods:
            method_info = method
            methods.append(method_info)

        token['methods'] = methods

        user = {}
        user['domain'] = {}

        user['id'] = access_token.user.id
        user['name'] = access_token.user.name
        user['domain']['id'] = access_token.user.domain.id
        user['domain']['name'] = access_token.user.domain.name

        token['user'] = user

        if access_token.catalog:
            catalog = []

            for service in access_token.catalog:
                service_info = {}
                service_info['id'] = service.id
                service_info['type'] = service.type
                service_info['name'] = service.name

                endpoints = []

                for endpoint in service.endpoints:
                    endpoint_info = {}
                    endpoint_info['id'] = endpoint.id
                    endpoint_info['region'] = endpoint.region
                    endpoint_info['region_id'] = endpoint.region_id
                    endpoint_info['interface'] = endpoint.interface
                    endpoint_info['url'] = endpoint.url
                    endpoints.append(endpoint_info)

                service_info['endpoints'] = endpoints
                catalog.append(service_info)

            token['catalog'] = catalog

        roles = []

        for role in access_token.roles:
            role_info = {}
            role_info['id'] = role.id
            role_info['name'] = role.name
            roles.append(role_info)

        token['roles'] = roles

        if hasattr(access_token, 'project'):
            project = {}
            project['domain'] = {}
            project['id'] = access_token.project.id
            project['name'] = access_token.project.name
            project['domain']['id'] = access_token.project.domain.id
            project['domain']['name'] = access_token.project.domain.name

            token['project'] = project

        if hasattr(access_token, 'domain'):
            domain = {}
            domain['id'] = access_token.domain.id
            domain['name'] = access_token.domain.name

            token['domain'] = domain

        if access_token.federation:
            groups = []
            for group in access_token.federation.groups:
                group_info = []
                group_info['id'] = group['id']
                groups.append(group_info)

            federation = {}
            federation['identity_provider'] =\
                access_token.federation.identity_provider
            federation['protocol'] = access_token.federation.protocol
            federation['groups'] = groups

            token['OS-FEDERATION'] = federation

        if hasattr(access_token, 'trust'):
            trust = {}
            trust['trustor_user'] = {}
            trust['trustee_user'] = {}
            trust['id'] = access_token.trust.id
            trust['impersonation'] = access_token.trust.impersonation
            trust['trustor_user']['id'] = access_token.trust.trustor_user
            trust['trustee_user']['id'] = access_token.trust.trustee_user

            token['OS-TRUST:trust'] = trust

        if hasattr(access_token, 'oauth'):
            oauth = {}
            oauth['consumer_id'] = access_token.oauth.consumer_id
            oauth['access_token_id'] = access_token.oauth.access_token_id

            token['OS-OAUTH1'] = oauth

        token_data['token'] = token

        return token_data
