# -*- coding: utf-8 -*-
# Copyright 2012 OpenStack Foundation
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

from keystone.common import driver_hints
import keystone.conf
from keystone.credential.providers import fernet as credential_provider
from keystone.tests import unit
from keystone.tests.unit import default_fixtures
from keystone.tests.unit import ksfixtures
from keystone.tests.unit.ksfixtures import database
from six.moves import range
import uuid

CONF = keystone.conf.CONF

class SqlTests(unit.SQLDriverOverrides, unit.TestCase):


    def setUp(self):
        super(SqlTests, self).setUp()
        self.useFixture(database.Database())
        self.load_backends()
        # populate the engine with tables & fixtures
        self.load_fixtures(default_fixtures)
        # defaulted by the data load
        self.user_foo['enabled'] = True

    def config_files(self):
        config_files = super(SqlTests, self).config_files()
        config_files.append(unit.dirs.tests_conf('backend_sql.conf'))
        return config_files


class SqlCredential(SqlTests):

    def _create_credential_with_user_id(self, user_id=uuid.uuid4().hex):
        credential = unit.new_credential_ref(user_id=user_id,
                                             extra=uuid.uuid4().hex,
                                             type=uuid.uuid4().hex)
        self.credential_api.create_credential(credential['id'], credential)
        return credential

    def _validateCredentialList(self, retrieved_credentials,
                                expected_credentials):
        self.assertEqual(len(expected_credentials), len(retrieved_credentials))
        retrived_ids = [c['id'] for c in retrieved_credentials]
        for cred in expected_credentials:
            self.assertIn(cred['id'], retrived_ids)

    def setUp(self):
        self.useFixture(database.Database())
        super(SqlCredential, self).setUp()
        self.useFixture(
            ksfixtures.KeyRepository(
                self.config_fixture,
                'credential',
                credential_provider.MAX_ACTIVE_KEYS
            )
	)
	self.credentials = []
        self.user_credentials = []
        for _ in range(3):
            cred = self._create_credential_with_user_id()
            self.user_credentials.append(cred)
            self.credentials.append(cred)
        for _ in range(3):
            cred = self._create_credential_with_user_id(self.user_foo['id'])
            self.user_credentials.append(cred)
            self.credentials.append(cred)

    def test_sqlalchemy_bug_hints_None(self):
        hints = driver_hints.Hints()
        hints.add_filter('key_hash', None, comparator='notlike')
        credentials = self.credential_api.list_credentials(hints=None)
        self._validateCredentialList(credentials, self.user_credentials)

    def test_sqlalchemy_bug_hints(self):
        hints = driver_hints.Hints()
        hints.add_filter('key_hash', None, comparator='notlike')
        credentials = self.credential_api.list_credentials(hints)
        self._validateCredentialList(credentials, self.user_credentials)

    def test_sqlalchemy_bug_no_hints(self):
        hints = driver_hints.Hints()
        hints.add_filter('key_hash', None, comparator='notlike')
        credentials = self.credential_api.list_credentials()
        self._validateCredentialList(credentials, self.user_credentials)
