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

from keystone.common.ldap import core
from keystone import exception
from keystone.tests.unit import BaseTestCase


class LdapConfigDistinguishedNameTests(BaseTestCase):

    def test_user_tree_dn_with_invalid_char_back_slash(self):
        config = {'ldap': {'url': uuid.uuid4().hex,
                           'user_tree_dn':
                               'CN=user1, CN=user\s, DC=Contoso, DC=com',
                           'password': uuid.uuid4().hex}}

        self._assert_raises_InvalidDomainConfig(config)

    def test_user_tree_dn_with_invalid_char_lessthan(self):
        config = {'ldap': {'url': uuid.uuid4().hex,
                           'user_tree_dn':
                               'CN=user1, CN=user<s, DC=Contoso, DC=com',
                           'password': uuid.uuid4().hex}}

        self._assert_raises_InvalidDomainConfig(config)

    def test_group_tree_dn_with_invalid_char_semicolon(self):
        config = {'ldap': {'url': uuid.uuid4().hex,
                           'group_tree_dn':
                               'CN=user1, CN=users, DC=Cont;oso, DC=com',
                           'password': uuid.uuid4().hex}}

        self._assert_raises_InvalidDomainConfig(config)

    def test_user_with_invalid_char_comma(self):
        config = {
            'ldap': {'url': 'fake://memory',
                     'user': 'cn=Adm,in',
                     'password': 'password',
                     'suffix': 'cn=example,cn=com'},
            'identity': {'driver': 'ldap'}
        }
        self._assert_raises_InvalidDomainConfig(config)

    def _assert_raises_InvalidDomainConfig(self, config):
        self.assertRaises(exception.InvalidDomainConfig,
                          core.validate_config_dn,
                          config)
