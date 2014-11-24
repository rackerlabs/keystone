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
import copy
import datetime

from oslo_utils import timeutils
import six


# gap, in seconds, to determine whether the given token is about to expire
STALE_TOKEN_DURATION = 30


def assert_string(obj):
    if not isinstance(obj, six.string_types):
        raise ValueError('%s not a string' % obj)
    return obj


def assert_class(cls, obj):
    if type(obj) != cls:
        raise ValueError('%s not of class %s ' %
                         (type(obj).__name__, cls.__name__))


def assert_datetime(obj):
    assert_class(datetime.datetime, obj)
    if obj.tzinfo is None:
        raise ValueError('Timezone information missing from datetime')


def assert_is_instance(cls, obj):
    if not isinstance(obj, cls):
        raise ValueError('%s not of class %s ' %
                         (type(obj).__name__, cls.__name__))


class DateString(six.text_type):
    def __init__(self, value):
        assert_datetime(value)
        self.value = value

    def __new__(cls, value):
        # The Python 3 version of this would be
        # return super().__new__(cls, value)
        # But that will not work for Python 2.7.
        # The following works for both.
        strval = timeutils.strtime(value)
        return six.text_type.__new__(cls, strval)

    def __eq__(self, other):
        """Compare this DateString to another object.

        Supports comparing with other strings that represent dates,
        comparing with datetime.datetime or other DateString objects.
        """
        if isinstance(other, DateString):
            return self.value == other.value
        elif isinstance(other, datetime.datetime):
            return self.value == other
        elif isinstance(other, six.string_types):
            other_date = timeutils.parse_isotime(other)
            return self.value == other_date
        return False

    def utcoffset(self):
        return self.value.utcoffset()

    def replace(self, *args, **kwargs):
        return self.value.replace(*args, **kwargs)

    def strftime(self, format):
        return self.value.strftime(format)

    @property
    def tzinfo(self):
        return self.value.tzinfo


class Immutable(object):
    _is_immutable = False

    def __setattr__(self, att, v):
        """Enforce object is immutable after `lock` has been called."""
        if self._is_immutable is False:
            super(Immutable, self).__setattr__(att, v)
        else:
            raise AttributeError('Attempt to modify immutable object.')

    def get(self, attr, default=None):
        try:
            return self.__dict__[attr]
        except KeyError:
            return default

    def __getitem__(self, attr):
        """Return member variable for iteration."""
        return self.__dict__[attr]

    def lock(self):
        self._is_immutable = True

    def iteritems(self, **kwargs):
        return six.iteritems(self.__dict__, **kwargs)

    def items(self, **kwargs):
        return six.iteritems(self.__dict__, **kwargs)

    def __iter__(self):
        """Generate iterator based on members variables."""
        for key in dir(self):
            yield key


class TypeSafeList(list):
    """List where all members in list are of type `item_class`."""

    def __init__(self, item_class, items):
        self._item_class = item_class
        for item in items:
            assert_class(self._item_class, item)
            self.append(item)

    def __setitem__(self, key, item):
        """Check that item is subclass of type `item_class`."""
        assert_class(self._item_class, item)
        super(TypeSafeList, self).__setitem__(key, item)

    def append(self, item):
        assert_class(self._item_class, item)
        super(TypeSafeList, self).append(item)


class SubclassList(list):
    """List where all members in list are subclasses of type `item_class`."""

    def __init__(self, item_class, items):
        self._item_class = item_class
        for item in items:
            assert_is_instance(self._item_class, item)
            self.append(item)

    def __setitem__(self, key, item):
        """Check that item is subclass of type `item_class`."""
        assert_is_instance(self._item_class, item)
        super(SubclassList, self).__setitem__(key, item)

    def append(self, item):
        assert_is_instance(self._item_class, item)
        super(SubclassList, self).append(item)


class Domain(Immutable):
    def __init__(self, id, name):
        self.id = id
        self.name = name


class Role(Immutable):
    def __init__(self, id, name):
        self.id = id
        assert_string(name)
        self.name = name


class User(Immutable):
    def __init__(self, id, name, domain):
        self.domain = domain
        self.id = id
        self.name = name


class Endpoint(Immutable):
    def __init__(self, id, region):
        if id is not None:
            self.id = assert_string(id)
        if region is not None:
            self.region = assert_string(region)


class V3Endpoint(Endpoint):
    def __init__(self, id, interface, region, region_id, url):
        super(V3Endpoint, self).__init__(id, region)
        if (id is None):
            raise ValueError('id must not be none for V3 endpoint')
        self.interface = assert_string(interface)
        self.url = assert_string(url)
        if region_id is not None:
            self.region_id = assert_string(region_id)


class V2Endpoint(Endpoint):
    # The Endpoint is a subset of these values, all of them are optional
    def __init__(self, id, tenantId, region, interface,
                 publicURL, internalURL, adminURL,
                 versionInfo, versionList, versionId):
        super(V2Endpoint, self).__init__(id, region)
        if tenantId is not None:
            self.tenantId = tenantId
        if publicURL is not None:
            self.publicURL = publicURL
        if internalURL is not None:
            self.internalURL = internalURL
        if adminURL is not None:
            self.adminURL = adminURL
        if versionInfo is not None:
            self.versionInfo = versionInfo
        if versionList is not None:
            self.versionList = versionList
        if versionId is not None:
            self.versionId = versionId


class Service(Immutable):
    def __init__(self, id, type, name, endpoints):
        self.id = id
        self.type = type
        self.name = name
        self.endpoints = SubclassList(Endpoint, endpoints)


class Catalog(TypeSafeList):
    def __init__(self, services):
        super(Catalog, self).__init__(Service, services)


class Project(Immutable):
    def __init__(self, id, name, domain):
        assert_class(Domain, domain)
        self.id = id
        self.name = name
        self.domain = domain


class ServiceProvider(Immutable):
    def __init__(self, id, auth_url, sp_url):
        self.id = id
        self.auth_url = auth_url
        self.sp_url = sp_url


class ServiceProviders(TypeSafeList):
    def __init__(self, service_providers):
        super(ServiceProviders, self).__init__(ServiceProvider,
                                               service_providers)


class Trust(Immutable):
    def __init__(self, id, impersonation, trustor_user_id, trustee_user_id):
        self.impersonation = bool(impersonation)
        self.id = id
        self.trustor_user_id = trustor_user_id
        self.trustee_user_id = trustee_user_id


class Oauth(Immutable):
    def __init__(self, consumer_id, access_token_id):
        self.consumer_id = consumer_id
        self.access_token_id = access_token_id


class Group(Immutable):
    def __init__(self, id):
        self.id = id


class Groups(TypeSafeList):
    def __init__(self, groups):
        super(Groups, self).__init__(Group, groups)


class Federation(Immutable):
    def __init__(self, identity_provider, protocol, groups):
        self.identity_provider = identity_provider
        self.protocol = protocol
        self.groups = groups


class Token(Immutable):
    def __init__(self, user, catalog, roles, expires_at, issued_at, methods,
                 scope, delegation=None, federation=None, audit_ids=None,
                 service_providers=None):
        audit_ids = audit_ids or []
        assert_class(User, user)
        if isinstance(scope, Project):
            self.project = scope
        elif isinstance(scope, Domain):
            self.domain = scope
        elif scope is None:
            self.scope = None
        else:
            raise ValueError('Scope must be project, domain, or None')

        self.expires_at = DateString(expires_at)
        self.issued_at = DateString(issued_at)
        self.methods = methods
        self.user = user

        if catalog is not None:
            assert_class(Catalog, catalog)
        self.catalog = catalog

        self.roles = roles
        self.audit_ids = copy.deepcopy(audit_ids)
        if delegation is not None:
            if isinstance(delegation, Trust):
                self.trust = delegation
            elif isinstance(delegation, Oauth):
                self.oauth = delegation
        if federation is not None:
            assert_class(Federation, federation)
        self.federation = federation

        if service_providers is not None:
            assert_class(ServiceProviders, service_providers)
        self.service_providers = service_providers
