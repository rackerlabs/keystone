# Copyright 2016 Red Hat, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import time

from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions as lib_exc

from keystone import conf as keystone_conf
from keystone_tempest_plugin.tests import base


KEYSTONE_CONF = keystone_conf.CONF


class TestSecurityCompliance(base.BaseIdentityTest):

    @classmethod
    def resource_setup(cls):
        super(TestSecurityCompliance, cls).resource_setup()
        cls.user_name = data_utils.rand_name('user')
        cls.user_password = data_utils.rand_password()

        cls.domain = cls.domains_client.create_domain(
            data_utils.rand_name('domain'))['domain']
        cls.project = cls.projects_client.create_project(
            data_utils.rand_name('project'),
            domain_id=cls.domain['id'])['project']
        cls.user = cls.users_client.create_user(
            name=cls.user_name,
            password=cls.user_password,
            domain_id=cls.domain['id'])['user']
        cls.role = cls.roles_client.create_role(
            name=data_utils.rand_name('Role'))['role']
        cls.roles_client.create_user_role_on_project(
            cls.project['id'], cls.user['id'], cls.role['id'])

    @classmethod
    def resource_cleanup(cls):
        cls.roles_client.delete_role_from_user_on_project(
            cls.project['id'], cls.user_body['id'], cls.role['id'])
        cls.roles_client.delete_role(cls.role['id'])
        cls.users_client.delete_user(cls.user_body['id'])
        cls.projects_client.delete_project(cls.project['id'])
        cls.domains_client.update_domain(cls.domain['id'], enabled=False)
        cls.domains_client.delete_domain(cls.domain['id'])
        super(TestSecurityCompliance, cls).resource_cleanup()

    def _login_kwargs(self, **kwargs):
        kwargs.setdefault('username', self.user_name)
        kwargs.setdefault('password', self.user_password)
        kwargs.setdefault('project_name', self.project['name'])
        kwargs.setdefault('user_domain_id', self.domain['id'])
        kwargs.setdefault('project_domain_id', self.domain['id'])
        return kwargs

    def test_user_account_lockout(self):
        failure_attempts = (
            KEYSTONE_CONF.security_compliance.lockout_failure_attempts)
        # Lock user account by using the wrong password to login
        bad_password = data_utils.rand_password()
        for i in range(failure_attempts):
            self.token_client.auth(
                **self._login_kwargs(password=bad_password))

        # Now it is not possible to login even using the correct password
        self.assertRaises(lib_exc.Forbidden,
                          self.token_client.auth,
                          **self._login_kwargs())

        # If we wait the required time, the user account will be unlocked
        time.sleep(KEYSTONE_CONF.security_compliance.lockout_duration)

        self.token_client.auth(**self._login_kwargs())

    def test_password_uniqueness_requirements(self):
        last_passwords_count = (
            KEYSTONE_CONF.security_compliance.unique_last_password_count)
        if last_passwords_count > 1:
            # Can not reuse an old password
            self.assertRaises(lib_exc.Forbidden,
                              self.users_client.update,
                              user_id=self.user['id'],
                              password=self.user_password)

        # Although is possible to set a new password
        password = data_utils.rand_password()
        self.users_client.update(self.user['id'], password=password)
