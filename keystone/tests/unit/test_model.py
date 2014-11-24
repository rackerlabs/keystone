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

from datetime import datetime
import uuid

from oslo_serialization import jsonutils
from oslo_utils import timeutils
import six
import testtools

from keystone.models import builder
from keystone.models import core


class ModelTestCase(testtools.TestCase):

    def setUp(self):
        super(ModelTestCase, self).setUp()

        self.dom_id = uuid.uuid4().hex
        self.user_id = uuid.uuid4().hex

    def test_create_user(self):
        domain = core.Domain(self.dom_id, uuid.uuid4().hex)
        user = core.User(self.user_id, uuid.uuid4().hex, domain)
        self.assertEqual(user['id'], self.user_id)
        self.assertEqual(user['domain']['id'], self.dom_id)

    def test_class(self):
        try:
            core.Role('u2', 4)
            self.fail()
        except ValueError:
            pass

    def test_immutable(self):
        try:
            domain = core.Domain('id', 'name')
            domain.lock()
            domain.name = "should not work"
            self.fail()
        except AttributeError:
            pass

    def test_builder_unscoped(self):
        director = builder.PythonDirector()
        access = director.construct(access_data_unscoped)
        self.assertIsNotNone(access)
        self.assert_deep_match(access_data_unscoped['token'], access)

    def test_builder_project_scoped(self):
        director = builder.PythonDirector()
        access = director.construct(access_data_project_scoped)
        self.assertIsNotNone(access)
        self.assert_deep_match(access_data_project_scoped['token'], access)

    def test_builder_domain_scoped_domain(self):
        director = builder.PythonDirector()
        access = director.construct(access_data_domain_scoped)
        self.assertIsNotNone(access)

    def assert_list_match(self, first, second):
        index = 0
        a = []
        b = []

        for item in first:
            if isinstance(item, six.string_types):
                a.append(item)
                b.append(second[index])
            else:
                a.append(item['id'])
                b.append(second[index]['id'])
            index += 1

        a.sort()
        b.sort()
        for i in range(0, len(a)):
            self.assertEqual(a[i], b[i])

    def assert_catalog_match(self, first, second):
        for i in range(0, len(first)):
            self.assert_list_match(first[i]['endpoints'],
                                   second[i]['endpoints'])

    def assert_deep_match(self, first, second):
        for k, v in six.iteritems(first):
            if isinstance(v, six.string_types):
                if isinstance(v, core.DateString):
                    self.assertEqual(v, second[k])
                elif isinstance(second[k], datetime):
                    date_v = timeutils.parse_isotime(v)
                    self.assertEqual(date_v, second[k])
                else:
                    self.assertEqual(v, second[k])
            elif k == 'catalog':
                self.assert_catalog_match(v, second[k])
            elif isinstance(v, list):
                try:
                    self.assert_list_match(v, second[k])
                except KeyError:
                    print('failed testing %s' % k)
                    raise
            else:
                self.assert_deep_match(v, second[k])

    def _user_domain(self):
        dom_data = access_data_unscoped['token']['user']['domain']
        domain = core.Domain(dom_data['id'], dom_data['name'])

        return domain

    def test_encode_domain(self):
        encoded = jsonutils.loads(jsonutils.dumps(self._user_domain()))
        self.assert_deep_match(
            encoded,
            access_data_domain_scoped['token']['user']['domain'])

    def test_encode_user(self):
        user_data = access_data_unscoped['token']['user']
        user = core.User(user_data['id'], user_data['name'],
                         self._user_domain())
        encoded = jsonutils.loads(jsonutils.dumps(user))
        self.assert_deep_match(encoded,
                               access_data_unscoped['token']['user'])

    def test_encode_datestring(self):
        expires_at_datetime = timeutils.parse_isotime(
            access_data_unscoped['token']['expires_at'])
        expires_at = core.DateString(expires_at_datetime)
        jsonutils.dumps(expires_at)

    def test_encode_unscoped(self):

        director = builder.PythonDirector()
        access = director.construct(access_data_unscoped)
        jsonutils.dumps(access)
        self.assertEqual(access.user.id,
                         access_data_unscoped['token']['user']['id'])

    def test_encode_domain_scoped(self):
        director = builder.PythonDirector()
        access = director.construct(access_data_domain_scoped)
        jsonutils.dumps(access)
        self.assertEqual(access.domain.id,
                         access_data_domain_scoped['token']['domain']['id'])
        self.assertEqual(access.audit_ids,
                         access_data_domain_scoped['token']['audit_ids'])

    def test_encode_project_scoped(self):
        director = builder.PythonDirector()
        access = director.construct(access_data_project_scoped)
        jsonutils.dumps(access)
        self.assertEqual(access.project.id,
                         access_data_project_scoped['token']['project']['id'])
        self.assertEqual(access.audit_ids,
                         access_data_project_scoped['token']['audit_ids'])

    def test_encode_v2_scoped(self):

        director = builder.PythonDirector()
        access = director.construct(access_data_v2_scoped)
        jsonutils.dumps(access)
        self.assertEqual(access.project.id, 'tenant_id1')
        self.assertEqual(access.audit_ids,
                         access_data_v2_scoped['access']['token']['audit_ids'])


access_data_v2_scoped = {
    "access": {
        "token": {
            "audit_ids": [
                "rDdQE66dQ1KCw4Fac1Lp0g"
            ],
            "expires": "2038-01-18T21:14:07Z",
            "issued_at": "2002-01-18T21:14:07Z",
            "id": "placeholder",
            "tenant": {
                "id": "tenant_id1",
                "enabled": True,
                "description": None,
                "name": "tenant_name1"
            }
        },
        "serviceCatalog": [
            {
                "endpoints_links": [],
                "endpoints": [
                    {
                        "adminURL":
                        "http://127.0.0.1:8776/v1/" +
                        "64b6f3fbcc53435e8a60fcf89bb6617a",
                        "region": "regionOne",
                        "internalURL": "http://127.0.0.1:8776/v1/" +
                        "64b6f3fbcc53435e8a60fcf89bb6617a",
                        "publicURL": "http://127.0.0.1:8776/v1/" +
                        "64b6f3fbcc53435e8a60fcf89bb6617a"
                    }
                ],
                "type": "volume",
                "name": "volume"
            },
            {
                "endpoints_links": [],
                "endpoints": [
                    {
                        "adminURL": "http://127.0.0.1:9292/v1",
                        "region": "regionOne",
                        "internalURL": "http://127.0.0.1:9292/v1",
                        "publicURL": "http://127.0.0.1:9292/v1"
                    }
                ],
                "type": "image",
                "name": "glance"
            },
            {
                "endpoints_links": [],
                "endpoints": [
                    {
                        "adminURL":
                        "http://127.0.0.1:8774/v1.1/" +
                        "64b6f3fbcc53435e8a60fcf89bb6617a",
                        "region": "regionOne",
                        "internalURL": "http://127.0.0.1:8774/v1.1/" +
                        "64b6f3fbcc53435e8a60fcf89bb6617a",
                        "publicURL":
                        "http://127.0.0.1:8774/v1.1/" +
                        "64b6f3fbcc53435e8a60fcf89bb6617a"
                    }
                ],
                "type": "compute",
                "name": "nova"
            },
            {
                "endpoints_links": [],
                "endpoints": [
                    {
                        "adminURL": "http://127.0.0.1:35357/v2.0",
                        "region": "RegionOne",
                        "internalURL": "http://127.0.0.1:35357/v2.0",
                        "publicURL": "http://127.0.0.1:5000/v2.0"
                    }
                ],
                "type": "identity",
                "name": "keystone"
            }
        ],
        "user": {
            "username": "user_name1",
            "roles_links": [
                "role1",
                "role2"
            ],
            "id": "user_id1",
            "roles": [
                {
                    "id": "f03fda8f8a3249b2a70fb1f176a7b631",
                    "name": "role1"
                },
                {
                    "id": "f03fda8f8a3249b2a70fb1f176a7b631",
                    "name": "role2"
                }
            ],
            "name": "user_name1"
        }
    }
}


access_data_unscoped = {
    "token": {
        "expires_at": "2013-02-27T18:30:59.999999Z",
        "issued_at": "2013-02-27T16:30:59.999999Z",
        "methods": [
            "password"
        ],
        "user": {
            "domain": {
                "id": "1789d1",
                "name": "example.com"
            },
            "id": "0ca8f6",
            "name": "Joe"
        }
    }
}


access_data_project_scoped = {
    "token": {
        "audit_ids": ["VcxU2JYqT8OzfUVvrjEITQ", "qNUTIJntTzO1-XUk5STybw"],
        "catalog": [
            {
                "endpoints": [
                    {
                        "id": "39dc322ce86c4111b4f06c2eeae0841b",
                        "interface": "public",
                        "region": "RegionOne",
                        "region_id": "RegionOne",
                        "url": "http://localhost:5000"
                    },
                    {
                        "id": "ec642f27474842e78bf059f6c48f4e99",
                        "interface": "internal",
                        "region": "RegionOne",
                        "region_id": "RegionOne",
                        "url": "http://localhost:5000"
                    },
                    {
                        "id": "c609fc430175452290b62a4242e8a7e8",
                        "interface": "admin",
                        "region": "RegionOne",
                        "region_id": "RegionOne",
                        "url": "http://localhost:35357"
                    }
                ],
                "id": "4363ae44bdf34a3981fde3b823cb9aa2",
                "type": "identity",
                "name": "keystone"
            }
        ],
        "expires_at": "2013-02-27T18:30:59.999999Z",
        "issued_at": "2013-02-27T16:30:59.999999Z",
        "methods": [
            "password"
        ],
        "project": {
            "domain": {
                "id": "1789d1",
                "name": "example.com"
            },
            "id": "263fd9",
            "name": "project-x"
        },
        "roles": [
            {
                "id": "76e72a",
                "name": "admin"
            },
            {
                "id": "f4f392",
                "name": "member"
            }
        ],
        "user": {
            "domain": {
                "id": "1789d1",
                "name": "example.com"
            },
            "id": "0ca8f6",
            "name": "Joe"
        }
    }
}


access_data_domain_scoped = {
    "token": {
        "audit_ids": ["1d2dddf926a54b7aaac0e1f351ae2497",
                      "64a9257adf77432e9c589061dabb6385"],
        "catalog": [
            {
                "endpoints": [
                    {
                        "id": "39dc322ce86c4111b4f06c2eeae0841b",
                        "interface": "public",
                        "region": "RegionOne",
                        "region_id": "RegionOne",
                        "url": "http://localhost:5000"
                    },
                    {
                        "id": "ec642f27474842e78bf059f6c48f4e99",
                        "interface": "internal",
                        "region": "RegionOne",
                        "region_id": "RegionOne",
                        "url": "http://localhost:5000"
                    },
                    {
                        "id": "c609fc430175452290b62a4242e8a7e8",
                        "interface": "admin",
                        "region": "RegionOne",
                        "region_id": "RegionOne",
                        "url": "http://localhost:35357"
                    }
                ],
                "id": "4363ae44bdf34a3981fde3b823cb9aa2",
                "type": "identity",
                "name": "keystone"
            }
        ],
        "expires_at": "2013-02-27T18:30:59.999999Z",
        "issued_at": "2013-02-27T16:30:59.999999Z",
        "methods": [
            "password"
        ],
        "domain": {
            "id": "1789d1",
            "name": "example.com"
        },
        "roles": [
            {
                "id": "76e72a",
                "name": "admin"
            },
            {
                "id": "f4f392",
                "name": "member"
            }
        ],
        "user": {
            "domain": {
                "id": "1789d1",
                "name": "example.com"
            },
            "id": "0ca8f6",
            "name": "Joe"
        },
        "service_providers": [
            {
                "auth_url": "https://example.com:5000/v3/OS-FEDERATION/" +
                "identity_providers/acme/protocols/saml2/auth",
                "id": "sp1",
                "sp_url": "https://example.com:5000/Shibboleth.sso/" +
                "SAML2/ECP"
            },
            {
                "auth_url": "https://other.example.com:5000/v3/" +
                "OS-FEDERATION/identity_providers/acme/protocols/saml2/" +
                "auth",
                "id": "sp2",
                "sp_url": "https://other.example.com:5000/" +
                "Shibboleth.sso/SAML2/ECP"
            }
        ],
    }
}
