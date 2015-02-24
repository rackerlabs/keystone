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

import copy
import uuid

from oslo_config import cfg

from keystone import exception
from keystone.tests.unit import test_v3


CONF = cfg.CONF


class DomainConfigTestCase(test_v3.RestfulTestCase):
    """Test database domain config support."""

    def setUp(self):
        super(DomainConfigTestCase, self).setUp()

        self.domain = {'id': uuid.uuid4().hex, 'name': uuid.uuid4().hex}
        self.resource_api.create_domain(self.domain['id'], self.domain)
        self.config = {'ldap': {'url': uuid.uuid4().hex,
                                'user_tree_dn': uuid.uuid4().hex},
                       'identity': {'driver': uuid.uuid4().hex}}

    def test_create_config(self):
        """Call ``PUT /domains/{domain_id}/config``."""
        r = self.put('/domains/%(domain_id)s/config' % {
            'domain_id': self.domain['id']},
            body={'config': self.config},
            expected_status=201)
        res = self.domain_config_api.get_config(self.domain['id'])
        self.assertEqual(self.config, r.result['config'])
        self.assertEqual(self.config, res)

    def test_create_config_twice(self):
        """Check multiple creates don't throw error"""
        self.put('/domains/%(domain_id)s/config' % {
            'domain_id': self.domain['id']},
            body={'config': self.config},
            expected_status=201)
        self.put('/domains/%(domain_id)s/config' % {
            'domain_id': self.domain['id']},
            body={'config': self.config},
            expected_status=201)

    def test_delete_config(self):
        """Call ``DELETE /domains{domain_id}/config``."""
        self.domain_config_api.create_config(self.domain['id'], self.config)
        self.delete('/domains/%(domain_id)s/config' % {
            'domain_id': self.domain['id']})
        self.get('/domains/%(domain_id)s/config' % {
            'domain_id': self.domain['id']},
            expected_status=exception.DomainConfigNotFound.code)

    def test_delete_config_by_group(self):
        """Call ``DELETE /domains{domain_id}/config/group``."""
        self.domain_config_api.create_config(self.domain['id'], self.config)
        self.delete('/domains/%(domain_id)s/config/ldap' % {
            'domain_id': self.domain['id']})
        res = self.domain_config_api.get_config(self.domain['id'])
        self.assertNotIn('ldap', res)

    def test_get_config(self):
        """Call ``GET /domains{domain_id}/config``."""
        self.domain_config_api.create_config(self.domain['id'], self.config)
        r = self.get('/domains/%(domain_id)s/config' % {
                     'domain_id': self.domain['id']})
        self.assertEqual(self.config, r.result['config'])

    def test_get_config_by_group(self):
        """Call ``GET /domains{domain_id}/config/group``."""
        self.domain_config_api.create_config(self.domain['id'], self.config)
        r = self.get('/domains/%(domain_id)s/config/ldap' % {
                     'domain_id': self.domain['id']})
        self.assertEqual({'ldap': self.config['ldap']}, r.result['config'])

    def test_get_config_by_option(self):
        """Call ``GET /domains{domain_id}/config/group/option``."""
        self.domain_config_api.create_config(self.domain['id'], self.config)
        r = self.get('/domains/%(domain_id)s/config/ldap/url' % {
                     'domain_id': self.domain['id']})
        self.assertEqual({'url': self.config['ldap']['url']},
                         r.result['config'])

    def test_update_config(self):
        """Call ``PATCH /domains/{domain_id}/config``."""
        self.domain_config_api.create_config(self.domain['id'], self.config)
        new_config = {'ldap': {'url': uuid.uuid4().hex}}
        r = self.patch('/domains/%(domain_id)s/config' % {
            'domain_id': self.domain['id']},
            body={'config': new_config},
            expected_status=201)
        res = self.domain_config_api.get_config(self.domain['id'])
        self.assertEqual(new_config, r.result['config'])
        self.assertEqual(new_config, res)

    def test_update_config_group(self):
        """Call ``PATCH /domains/{domain_id}/config/group``."""
        self.domain_config_api.create_config(self.domain['id'], self.config)
        new_config = {'ldap': {'url': uuid.uuid4().hex}}
        r = self.patch('/domains/%(domain_id)s/config/ldap' % {
            'domain_id': self.domain['id']},
            body={'config': new_config},
            expected_status=201)
        res = self.domain_config_api.get_config(self.domain['id'])
        expected_config = copy.deepcopy(self.config)
        expected_config['ldap'] = new_config['ldap']
        self.assertEqual(expected_config, r.result['config'])
        self.assertEqual(expected_config, res)

    def test_update_config_option(self):
        """Call ``PATCH /domains/{domain_id}/config/group/option``."""
        self.domain_config_api.create_config(self.domain['id'], self.config)
        new_config = {'url': uuid.uuid4().hex}
        r = self.patch('/domains/%(domain_id)s/config/ldap/url' % {
            'domain_id': self.domain['id']},
            body={'config': new_config},
            expected_status=201)
        res = self.domain_config_api.get_config(self.domain['id'])
        expected_config = copy.deepcopy(self.config)
        expected_config['ldap']['url'] = new_config['url']
        self.assertEqual(expected_config, r.result['config'])
        self.assertEqual(expected_config, res)
