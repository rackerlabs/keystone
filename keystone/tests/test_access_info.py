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

import uuid

import testtools

from keystone.models import access_info
from keystone.models import builder


class AccessTestCase(testtools.TestCase):

    def setUp(self):
        super(AccessTestCase, self).setUp()

        self.dom_id = uuid.uuid4().hex
        self.user_id = uuid.uuid4().hex

    def test_create_user(self):
        domain = access_info.Domain(self.dom_id, uuid.uuid4().hex)
        user = access_info.User(self.user_id, uuid.uuid4().hex, domain)
        self.assertEqual(user['id'], self.user_id)
        self.assertEqual(user['domain']['id'], self.dom_id)

    def test_class(self):
        try:
            access_info.User('u2', 'username', 'error')
            self.fail()
        except ValueError:
            pass

    def test_immutable(self):
        try:
            domain = access_info.Domain('id', 'name')
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
            if isinstance(item, basestring):
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
        for k, v in first.iteritems():
            if isinstance(v, basestring):
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
        "catalog": [
            {
                "endpoints": [
                    {
                        "id": "39dc322ce86c4111b4f06c2eeae0841b",
                        "interface": "public",
                        "region": "RegionOne",
                        "url": "http://localhost:5000"
                    },
                    {
                        "id": "ec642f27474842e78bf059f6c48f4e99",
                        "interface": "internal",
                        "region": "RegionOne",
                        "url": "http://localhost:5000"
                    },
                    {
                        "id": "c609fc430175452290b62a4242e8a7e8",
                        "interface": "admin",
                        "region": "RegionOne",
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
        "catalog": [
            {
                "endpoints": [
                    {
                        "id": "39dc322ce86c4111b4f06c2eeae0841b",
                        "interface": "public",
                        "region": "RegionOne",
                        "url": "http://localhost:5000"
                    },
                    {
                        "id": "ec642f27474842e78bf059f6c48f4e99",
                        "interface": "internal",
                        "region": "RegionOne",
                        "url": "http://localhost:5000"
                    },
                    {
                        "id": "c609fc430175452290b62a4242e8a7e8",
                        "interface": "admin",
                        "region": "RegionOne",
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
        }
    }
}
