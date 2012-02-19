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

import os

import sqlite3

from keystone.common.sql import nova
from keystone.common.sql import util as sql_util
from keystone import config
from keystone.contrib.ec2.backends import sql as ec2_sql
from keystone.identity.backends import sql as identity_sql
from keystone import test


CONF = config.CONF


FIXTURE = {
    "users": [
        {"id": "testuser", "name": None},
        {"id": "testadmin", "name": None},
        {"id": "testuser2", "name": "Test User 2"},
        {"id": "testuser3", "name": None},
    ],
    "roles": ["sysadmin", "netadmin", "newrole"],
    "role_user_tenant_list": [
        {
            "user_id": "testuser",
            "role": "sysadmin",
            "tenant_id": "userproject"
        },
        {
            "user_id": "testuser",
            "role": "netadmin",
            "tenant_id": "userproject"
        },
        {
            "user_id": "testadmin",
            "role": "sysadmin",
            "tenant_id": "adminproject"
        },
        {
            "user_id": "testuser2",
            "role": "sysadmin",
            "tenant_id": "userproject"
        },
        {
            "user_id": "testuser2",
            "role": "sysadmin",
            "tenant_id": "user2project"
        },
        {
            "user_id": "testuser2",
            "role": "netadmin",
            "tenant_id": "user2project"
        },
        {
            "user_id": "testuser3",
            "role": "newrole",
            "tenant_id": "userproject"
        },
    ],
    "user_tenant_list": [
        {"tenant_id": "userproject", "user_id": "testuser"},
        {"tenant_id": "adminproject", "user_id": "testadmin"},
        {"tenant_id": "userproject", "user_id": "testuser2"},
        {"tenant_id": "user2project", "user_id": "testuser2"},
        {"tenant_id": "userproject", "user_id": "testuser3"},
    ],
    "ec2_credentials": [
        {
            "access_key": "myaccess",
            "secret_key": "mysecret",
            "user_id": "testuser",
        },
        {
            "access_key": "myaccess",
            "secret_key": "mysecret",
            "user_id": "testadmin",
        },
        {
            "access_key": "myaccess2",
            "secret_key": "mysecret2",
            "user_id": "testuser2",
        },
        {
            "access_key": "myaccess3",
            "secret_key": "mysecret3",
            "user_id": "testuser3",
        },
    ],
    "tenants": [
        {
            "description": "mydescription",
            "id": "userproject",
            "name": "userproject",
        },
        {
            "description": "mydescription",
            "id": "adminproject",
            "name": "adminproject",
        },
        {
            "description": "mydescription",
            "id": "user2project",
            "name": "user2project",
        },
    ],
}


class MigrateNovaAuth(test.TestCase):
    def setUp(self):
        super(MigrateNovaAuth, self).setUp()
        CONF(config_files=[test.etcdir('keystone.conf'),
                           test.testsdir('test_overrides.conf'),
                           test.testsdir('backend_sql.conf')])
        sql_util.setup_test_database()
        self.identity_api = identity_sql.Identity()
        self.ec2_api = ec2_sql.Ec2()

    def setup_old_database(self, sql_dump):
        sql_path = test.testsdir(sql_dump)
        db_path = test.testsdir('%s.db' % sql_dump)
        try:
            os.unlink(db_path)
        except OSError:
            pass
        script_str = open(sql_path).read().strip()
        conn = sqlite3.connect(db_path)
        conn.executescript(script_str)
        conn.commit()
        return db_path

    def test_export_diablo(self):
        db_path = self.setup_old_database('nova_diablo.sqlite')
        output = nova.export_auth('sqlite:///%s' % db_path)
        self.assertEqual(output, FIXTURE)

    def test_import(self):
        nova.import_auth(FIXTURE)

        users = {}
        for user in ['testuser', 'testuser2', 'testuser3', 'testadmin']:
            users[user] = self.identity_api.get_user_by_name(user)

        tenants = {}
        for tenant in ['userproject', 'user2project', 'adminproject']:
            tenants[tenant] = self.identity_api.get_tenant_by_name(tenant)

        membership_map = {
            'testuser': ['userproject'],
            'testuser2': ['userproject', 'user2project'],
            'testuser3': ['userproject'],
            'testadmin': ['adminproject'],
        }

        for (old_user, old_tenants) in membership_map.items():
            user = users[old_user]
            membership = self.identity_api.get_tenants_for_user(user['id'])
            expected = [tenants[t]['id'] for t in old_tenants]
            self.assertEqual(set(expected), set(membership))

        for ec2_cred in FIXTURE['ec2_credentials']:
            user_id = users[ec2_cred['user_id']]['id']
            for tenant_id in self.identity_api.get_tenants_for_user(user_id):
                access = '%s:%s' % (tenant_id, ec2_cred['access_key'])
                cred = self.ec2_api.get_credential(access)
                actual = cred['secret']
                expected = ec2_cred['secret_key']
                self.assertEqual(expected, actual)

        roles = self.identity_api.list_roles()
        role_names = set([role['name'] for role in roles])
        self.assertEqual(role_names, set(['netadmin', 'sysadmin', 'newrole']))

        assignment_map = {
            'testuser': {
                'userproject': ['sysadmin', 'netadmin'],
            },
            'testuser2': {
                'userproject': ['sysadmin'],
                'user2project': ['sysadmin', 'netadmin'],
            },
            'testuser3': {
                'userproject': ['newrole']
            },
            'testadmin': {
                'adminproject': ['sysadmin'],
            },
        }

        for (old_user, old_tenant_map) in assignment_map.items():
            tenant_names = ['userproject', 'user2project', 'adminproject']
            for tenant_name in tenant_names:
                user = users[old_user]
                tenant = tenants[tenant_name]
                roles = self.identity_api.get_roles_for_user_and_tenant(
                                user['id'], tenant['id'])
                actual = [self.identity_api.get_role(role_id)['name'] \
                            for role_id in roles]
                expected = old_tenant_map.get(tenant_name, [])
                self.assertEqual(set(actual), set(expected))

        # User should be unusable with password set to None by default
        user = self.identity_api.get_user_by_name('testuser2')
        tenant = self.identity_api.get_tenant_by_name('user2project')
        self.assertRaises(AssertionError, self.identity_api.authenticate,
                          user['id'], tenant['id'], None)

        # Update password and user should now be able to authenticate
        user['password'] = 'secrete'
        self.identity_api.update_user(user['id'], user)
        self.identity_api.authenticate(user['id'], tenant['id'], 'secrete')
