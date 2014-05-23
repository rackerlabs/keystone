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


import ldappool


from keystone.common.ldap import core as ldap_core
from keystone import config
from keystone import tests
from keystone.tests import fakeldap
from keystone.tests import test_backend_ldap_pool
from keystone.tests import test_ldap_livetest


CONF = config.CONF


class LiveLDAPPoolIdentity(test_ldap_livetest.LiveLDAPIdentity,
                           test_backend_ldap_pool.LdapPoolCommonTestMixin):
    """Executes existing ldap live test with pooled ldap handler to make
    sure it works without any error.

    Also executes pool specific tests via Mixin
    """

    def setUp(self):
        self._ldap_skip_live()
        super(LiveLDAPPoolIdentity, self).setUp()

    def config_files(self):
        config_files = super(LiveLDAPPoolIdentity, self).config_files()
        config_files.append(tests.dirs.
                            tests_conf('backend_pool_liveldap.conf'))
        return config_files

    def config_overrides(self):
        super(LiveLDAPPoolIdentity, self).config_overrides()
        self.config_fixture.config(
            group='identity',
            driver='keystone.identity.backends.ldap.Identity')

    def tearDown(self):
        # remove pool changes in a test if any
        ldap_core.CONNECTION_POOLS.pop(CONF.ldap.url, None)
        super(LiveLDAPPoolIdentity, self).tearDown()

    def test_assert_connector_used_not_fake_ldap_pool(self):
        handler = ldap_core._get_connection(CONF.ldap.url, use_pool=True)
        self.assertNotEqual(type(handler.Connector),
                            type(fakeldap.FakeLdapPool))
        self.assertEqual(type(handler.Connector),
                         type(ldappool.StateConnector))
