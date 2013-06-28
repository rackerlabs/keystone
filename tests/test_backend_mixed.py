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

import nose

from keystone import test

from keystone.common import sql
from keystone import config

import default_fixtures
import test_backend_ldap


CONF = config.CONF
DEFAULT_DOMAIN_ID = CONF.identity.default_domain_id


class LdapSqldentity(sql.Base, test.TestCase,
                     test_backend_ldap.BaseLDAPIdentity):

    def _set_config(self):
        self.config([test.etcdir('keystone.conf.sample'),
                     test.testsdir('test_overrides.conf'),
                     test.testsdir('backend_ldap_sql.conf')])

    def setUp(self):
        self._set_config()
        self.clear_database()
        self.load_backends()
        self.engine = self.get_engine()
        sql.ModelBase.metadata.create_all(bind=self.engine)
        self.load_fixtures(default_fixtures)
        #defaulted by the data load
        self.user_foo['enabled'] = True

    def tearDown(self):
        sql.ModelBase.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        sql.set_global_engine(None)

    def test_domain_crud(self):
        pass

    def test_list_domains(self):
        domains = self.identity_api.list_domains()
        self.assertEquals(
            domains,
            [{'description':
              (u'Owns users and tenants (i.e. projects)'
               ' available on Identity API v2.'),
              'enabled': True,
              'id': u'default',
              'name': u'Default'}])

    def test_project_filter(self):
        raise nose.exc.SkipTest(
            'N/A: Not part of SQL backend')

    def test_role_filter(self):
        raise nose.exc.SkipTest(
            'N/A: Not part of SQL backend')
