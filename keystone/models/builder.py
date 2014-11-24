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


from keystone.models import access_info


class Builder(object):
    def __init__(self):
        self.user_info = None
        self.methods = []
        self.roles = []
        self.scope = None
        self.services = dict()

    def add_method(self, method):
        self.methods.append(method)

    def set_expires_at(self, expires_at):
        self.expires_at = expires_at

    def set_issued_at(self, issued_at):
        self.issued_at = issued_at

    def add_user_info(self, user_info):
        self.user_info = user_info

    def add_user_domain_info(self, user_domain_info):
        self.user_domain_info = user_domain_info

    def add_role(self, id, name):
        role = access_info.Role(id, name)
        role.lock()
        self.roles.append(role)

    def add_project_scope(self, project_data):
        scope_domain_data = project_data['domain']
        scope_domain = access_info.Domain(
            scope_domain_data['id'],
            scope_domain_data['name'],
        )
        self.scope = access_info.Project(
            project_data['id'],
            project_data['name'],
            scope_domain)

    def add_domain_scope(self, domain_data):
        self.scope = access_info.Domain(
            domain_data['id'],
            domain_data['name'],
        )

    def add_service(self, service_info):
        id = service_info['id']
        self.services['id'] = access_info.Service(
            id,
            service_info['type'],
            service_info['name'], [])

    def add_endpoint(self, service_id, endpoint_data):
        self.services['id'].endpoints.append(
            access_info.Endpoint(
                endpoint_data['id'],
                endpoint_data['interface'],
                endpoint_data['region'],
                endpoint_data['url']))

    def build(self):
        user_domain = access_info.Domain(
            self.user_domain_info['id'],
            self.user_domain_info['name'])
        user = access_info.User(
            self.user_info['id'],
            self.user_info['name'],
            user_domain)

        catalog = access_info.Catalog(self.services.values())

        token = access_info.Token(user, catalog, tuple(self.roles),
                                  self.expires_at, self.issued_at,
                                  self.methods, self.scope)
        return token


class PythonDirector(object):
    def construct(self, token_data):
        builder = Builder()
        header = token_data['token']
        user = header['user']

        builder.set_expires_at(header['expires_at'])
        builder.set_issued_at(header['issued_at'])

        methods = header.get('methods', [])
        for method in methods:
            builder.add_method(method)

        builder.add_user_info(user)
        builder.add_user_domain_info(user['domain'])

        for role in header.get('roles', []):
            builder.add_role(role['id'], role['name'])

        project_data = header.get('project')
        if project_data:
            builder.add_project_scope(project_data)

        domain_data = header.get('domain')
        if domain_data:
            builder.add_domain_scope(domain_data)

        catalog_data = header.get('catalog')
        if catalog_data:
            for service in catalog_data:
                builder.add_service(service)
                for endpoint in service['endpoints']:
                    builder.add_endpoint(service['id'], endpoint)
        return builder.build()
