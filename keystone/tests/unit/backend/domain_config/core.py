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

import uuid

from testtools import matchers

from keystone import exception


class DomainConfigTests(object):

    def setUp(self):
        self.domain = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.resource_api.create_domain(self.domain['id'], self.domain)
        self.addCleanup(self.clean_up_domain)

    def clean_up_domain(self):
        self.domain_config_api.delete_config(self.domain['id'])
        self.domain_config_api.delete_sensitive_config_option(
            self.domain['id'])
        self.domain['enabled'] = False
        self.resource_api.update_domain(self.domain['id'], self.domain)
        self.resource_api.delete_domain(self.domain['id'])
        del self.domain

    def test_whitelisted_domain_config_crud(self):
        config = {'ldap': {'url': uuid.uuid4().hex,
                           'user_tree_dn': uuid.uuid4().hex}}
        self.domain_config_api.create_config(self.domain['id'], config)
        res = self.domain_config_api.get_config(self.domain['id'])
        self.assertEqual(config, res)

        config['ldap']['url'] = uuid.uuid4().hex
        self.domain_config_api.update_config(self.domain['id'], config)
        res = self.domain_config_api.get_config(self.domain['id'])
        self.assertEqual(config, res)

        self.domain_config_api.delete_config(self.domain['id'])
        self.assertRaises(exception.DomainConfigNotFound,
                          self.domain_config_api.get_config, self.domain['id'])
        # ...and silent if we try to delete it again
        self.domain_config_api.delete_config(self.domain['id'])

    def test_sensitive_domain_config_crud(self):
        group = 'ldap'
        option = 'password'
        value = uuid.uuid4().hex
        self.domain_config_api.create_sensitive_config_option(
            self.domain['id'], group, option, value)
        res = self.domain_config_api.get_sensitive_config_option(
            self.domain['id'], group, option)
        config = {'group': group, 'option': option, 'value': value}
        self.assertEqual(config, res)

        value = uuid.uuid4().hex
        self.domain_config_api.update_sensitive_config_option(
            self.domain['id'], group, option, value)
        res = self.domain_config_api.get_sensitive_config_option(
            self.domain['id'], group, option)
        config = {'group': group, 'option': option, 'value': value}
        self.assertEqual(config, res)

        self.domain_config_api.delete_sensitive_config_option(
            self.domain['id'], group, option)
        self.assertRaises(exception.DomainConfigNotFound,
                          self.domain_config_api.get_sensitive_config_option,
                          self.domain['id'], group, option)
        # ...and silent if we try to delete it again
        self.domain_config_api.delete_sensitive_config_option(
            self.domain['id'], group, option)

    def test_list_sensitive_domain_config_crud(self):
        """Test you can list by domain and domain+group."""

        config1 = {'group': 'ldap', 'option': 'password',
                   'value': uuid.uuid4().hex}
        config2 = {'group': 'ldap', 'option': 'url',
                   'value': uuid.uuid4().hex}
        config3 = {'group': 'identity', 'option': 'caching',
                   'value': uuid.uuid4().hex}
        for config in [config1, config2, config3]:
            self.domain_config_api.create_sensitive_config_option(
                self.domain['id'], config['group'], config['option'],
                config['value'])

        # Try listing all items from a domain
        res = self.domain_config_api.list_sensitive_config_options(
            self.domain['id'])
        self.assertThat(res, matchers.HasLength(3))
        self.assertIn(res[0], [config1, config2, config3])

        # Try listing by domain and group
        res = self.domain_config_api.list_sensitive_config_options(
            self.domain['id'], group='ldap')
        self.assertThat(res, matchers.HasLength(2))
        self.assertIn(res[0], [config1, config2])

    def test_delete_sensitive_domain_configs(self):
        """Test you can delete by domain and domain+group."""

        config1 = {'group': 'ldap', 'option': 'password',
                   'value': uuid.uuid4().hex}
        config2 = {'group': 'ldap', 'option': 'url',
                   'value': uuid.uuid4().hex}
        config3 = {'group': 'identity', 'option': 'caching',
                   'value': uuid.uuid4().hex}
        for config in [config1, config2, config3]:
            self.domain_config_api.create_sensitive_config_option(
                self.domain['id'], config['group'], config['option'],
                config['value'])

        # Try deleting by domain and group
        res = self.domain_config_api.delete_sensitive_config_option(
            self.domain['id'], group='identity')
        res = self.domain_config_api.list_sensitive_config_options(
            self.domain['id'])
        self.assertThat(res, matchers.HasLength(2))
        self.assertIn(res[0], [config1, config2])

        # Try deleting all items from a domain
        res = self.domain_config_api.delete_sensitive_config_option(
            self.domain['id'])
        res = self.domain_config_api.list_sensitive_config_options(
            self.domain['id'])
        self.assertThat(res, matchers.HasLength(0))
