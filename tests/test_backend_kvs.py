# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
#
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

from keystone import exception
from keystone import test
from keystone.identity.backends import kvs as identity_kvs
from keystone.token.backends import kvs as token_kvs
from keystone.catalog.backends import kvs as catalog_kvs

import test_backend
import default_fixtures


class KvsIdentity(test.TestCase, test_backend.IdentityTests):
    def setUp(self):
        super(KvsIdentity, self).setUp()
        self.identity_api = identity_kvs.Identity(db={})
        self.load_fixtures(default_fixtures)

    def test_create_tenant_long_name_fails(self):
        tenant = {'id': 'fake1', 'name': 'a' * 65}
        self.assertRaises(exception.ValidationError,
                          self.identity_api.create_tenant,
                          'fake1',
                          tenant)

    def test_create_tenant_blank_name_fails(self):
        tenant = {'id': 'fake1', 'name': ''}
        self.assertRaises(exception.ValidationError,
                          self.identity_api.create_tenant,
                          'fake1',
                          tenant)

    def test_create_tenant_invalid_name_fails(self):
        tenant = {'id': 'fake1', 'name': None}
        self.assertRaises(exception.ValidationError,
                          self.identity_api.create_tenant,
                          'fake1',
                          tenant)
        tenant = {'id': 'fake1', 'name': 123}
        self.assertRaises(exception.ValidationError,
                          self.identity_api.create_tenant,
                          'fake1',
                          tenant)

    def test_update_tenant_blank_name_fails(self):
        tenant = {'id': 'fake1', 'name': 'fake1'}
        self.identity_api.create_tenant('fake1', tenant)
        tenant['name'] = ''
        self.assertRaises(exception.ValidationError,
                          self.identity_api.update_tenant,
                          'fake1',
                          tenant)

    def test_update_tenant_long_name_fails(self):
        tenant = {'id': 'fake1', 'name': 'fake1'}
        self.identity_api.create_tenant('fake1', tenant)
        tenant['name'] = 'a' * 65
        self.assertRaises(exception.ValidationError,
                          self.identity_api.update_tenant,
                          'fake1',
                          tenant)

    def test_update_tenant_invalid_name_fails(self):
        tenant = {'id': 'fake1', 'name': 'fake1'}
        self.identity_api.create_tenant('fake1', tenant)
        tenant['name'] = None
        self.assertRaises(exception.ValidationError,
                          self.identity_api.update_tenant,
                          'fake1',
                          tenant)

        tenant['name'] = 123
        self.assertRaises(exception.ValidationError,
                          self.identity_api.update_tenant,
                          'fake1',
                          tenant)


class KvsToken(test.TestCase, test_backend.TokenTests):
    def setUp(self):
        super(KvsToken, self).setUp()
        self.token_api = token_kvs.Token(db={})


class KvsCatalog(test.TestCase, test_backend.CatalogTests):
    def setUp(self):
        super(KvsCatalog, self).setUp()
        self.catalog_api = catalog_kvs.Catalog(db={})
        self.load_fixtures(default_fixtures)
        self._load_fake_catalog()

    def _load_fake_catalog(self):
        self.catalog_foobar = self.catalog_api._create_catalog(
            'foo', 'bar',
            {'RegionFoo': {'service_bar': {'foo': 'bar'}}})

    def test_get_catalog_bad_user(self):
        catalog_ref = self.catalog_api.get_catalog('foo' + 'WRONG', 'bar')
        self.assert_(catalog_ref is None)

    def test_get_catalog_bad_tenant(self):
        catalog_ref = self.catalog_api.get_catalog('foo', 'bar' + 'WRONG')
        self.assert_(catalog_ref is None)

    def test_get_catalog(self):
        catalog_ref = self.catalog_api.get_catalog('foo', 'bar')
        self.assertDictEqual(catalog_ref, self.catalog_foobar)
