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

"""Unified in-memory access model."""


def assert_class(cls, obj):
    if type(obj) != cls:
        raise ValueError("%s not of class %s " %
                         (type(obj).__name__, cls.__name__))


class Immutable(object):
    _is_immutable = False

    def __setattr__(self, att, v):
        if self._is_immutable is False:
            super(Immutable, self).__setattr__(att, v)
        else:
            raise AttributeError('attempt to modify immutable object')

    def __getitem__(self, attr):
        return self.__dict__[attr]

    def lock(self):
        self._is_immutable = True


class TypeSafeList(list):

    def __init__(self, item_class, items):
        self._item_class = item_class
        for item in items:
            assert_class(self._item_class, item)
            self.append(item)

    def __setitem__(self, key, item):
        assert_class(self._item_class, item)
        super(TypeSafeList, self).__setitem__(key, item)

    def append(self, item):
        assert_class(self._item_class, item)
        super(TypeSafeList, self).append(item)


class Domain(Immutable):
    def __init__(self, id, name):
        self.id = id
        self.name = name


class Role(Immutable):
    def __init__(self, id, name):
        self.id = id
        self.name = name


class User(Immutable):
    def __init__(self, id, name, domain):
        assert_class(Domain, domain)

        self.domain = domain
        self.id = id
        self.name = name


class Endpoint(Immutable):
    def __init__(self, id, interface, region, url):
        self.id = id
        self.interface = interface
        self.region = region
        self.url = url


class Service(Immutable):
    def __init__(self, id, type, name, endpoints):
        self.id = id
        self.type = type
        self.name = name
        self.endpoints = TypeSafeList(Endpoint, endpoints)


class Catalog(TypeSafeList):
    def __init__(self, services):
        super(Catalog, self).__init__(Service, services)


class Project(Immutable):
    def __init__(self, id, name, domain):
        assert_class(Domain, domain)
        self.id = id
        self.name = name
        self.domain = domain


class Token(Immutable):
    def __init__(self, user, catalog, roles, expires_at, issued_at, methods,
                 scope):
        assert_class(User, user)
        assert_class(Catalog, catalog)
        if isinstance(scope, Project):
            self.project = scope
        elif isinstance(scope, Domain):
            self.domain = scope
        elif scope is None:
            scope = None
        else:
            raise ValueError("Scope must be project, domain, or None")

        self.expires_at = expires_at
        self.issued_at = issued_at
        self.methods = methods
        self.user = user
        self.catalog = catalog
        self.roles = roles

    def token_to_auth_context(self):
        auth_context = {'token': self,
                        'is_delegated_auth': False}
        auth_context['user_id'] = self.user.id

        if self.project_scoped:
            auth_context['project_id'] = self.project.id
        elif self.domain_scoped:
            auth_context['domain_id'] = self.domain.id

        if self.trust_scoped:
            auth_context['is_delegated_auth'] = True
            auth_context['trust_id'] = self.trust.id
            auth_context['trustor_id'] = self.trust.trustor_user_id
            auth_context['trustee_id'] = self.trust.trustee_user_id
        else:
            auth_context['trust_id'] = None
            auth_context['trustor_id'] = None
            auth_context['trustee_id'] = None

        roles = self.role_names
        if roles:
            auth_context['roles'] = roles

        if self.oauth_scoped:
            auth_context['is_delegated_auth'] = True
            auth_context['consumer_id'] = self.oauth.consumer_id
            auth_context['access_token_id'] = self.oauth.access_token_id

        if self.is_federated_user:
            auth_context['group_ids'] = self.federation.group_ids

        return auth_context
