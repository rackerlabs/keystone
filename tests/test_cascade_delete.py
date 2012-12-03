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

import uuid
import sys

import sqlalchemy
import sys

from keystone import config
from keystone import identity

from keystone.common import sql

from keystone.identity.backends.sql import UserTenantMembership
from keystone.identity.backends.sql import UserProjectMetadata
from keystone.identity.backends.sql import User

from keystone.identity.controllers import RoleController

import test_backend_sql

CONF = config.CONF


class CascadeDeleteTests(test_backend_sql.SqlTests):
    def setUp(self):
        super(CascadeDeleteTests, self).setUp()

        # create and share a single sqlalchemy engine for testing
        self.engine = sql.Base().get_engine(allow_global_engine=False)
        self.metadata = sqlalchemy.MetaData()

        # populate the engine with tables & fixtures
        self.metadata.bind = self.engine

        # define names
        self.role_name = 'admin'
        self.tenant_name = 'ProjectX'

    def tearDown(self):
        # Delete the tenant
        tenant = self.identity_api.get_tenant_by_name(self.tenant_name)
        self.identity_api.delete_tenant(tenant['id'])
        super(CascadeDeleteTests, self).tearDown()

    def check_table(self, table, table_key, user_id, expected):
        session = self.identity_api.get_session()
        query = session.query(table)
        query = query.filter(table_key == user_id)
        users = query.all()
        self.assertEquals(len(users), expected)

    def check_user_tenant_membership(self, user_id, expected):
        self.check_table(UserTenantMembership,
                         UserTenantMembership.user_id,
                         user_id,
                         expected)
        self.check_table(UserProjectMetadata,
                         UserProjectMetadata.user_id,
                         user_id,
                         expected)
        self.check_table(User,
                         User.id,
                         user_id,
                         expected)

    def get_role_by_name(self, role_name):
        roles = self.identity_api.list_roles()
        for role in roles:
            if(role['name'] == role_name):
                return role['id']

    def create_objects(self):
        # create the tenant
        self.tenant_id = uuid.uuid4().hex
        tenant = {
            'id': self.tenant_id,
            'name': self.tenant_name}
        try:
            self.identity_api.create_tenant(self.tenant_id, tenant)
        except:
            tenant = self.identity_api.get_tenant_by_name(tenant_name)
            self.tenant_id = tenant['id']

        # create the user
        user_name = "FooX"
        self.user_id = uuid.uuid4().hex
        user = {'id': self.user_id,
                'name': user_name,
                'password': 'password'}
        try:
            self.identity_api.create_user(self.user_id, user)
        except:
            user = self.identity_api.get_user_by_name(user_name)
            self.user_id = user['id']

        # add user to tenant
        self.identity_api.add_user_to_tenant(self.tenant_id, self.user_id)

        # create the role
        self.role_id = uuid.uuid4().hex
        role = {'id': self.role_id,
                'name': self.role_name}
        try:
            self.identity_api.create_role(self.role_id, role)
        except:
            # retrieve the role
            self.role_id = self.get_role_by_name('admin')

        # associate user to a role
        try:
            self.identity_api.add_role_to_user_and_tenant(self.user_id,
                                                          self.tenant_id,
                                                          self.role_id)
        except:
            pass

    def test_delete_user_cascades_deletes(self):
        self.create_objects()

        # retrieve user_tenant_membership information
        self.check_user_tenant_membership(self.user_id, 1)

        # delete the user
        self.identity_api.delete_user(self.user_id)

        # ensures the record in the user_tenant_membership has been deleted
        self.check_user_tenant_membership(self.user_id, 0)

    def test_delete_role(self):
        self.create_objects()

        self.role_id = self.get_role_by_name(self.role_name)
        self.identity_api.delete_role(self.role_id)

        self.identity_api.get_roles_for_user_and_tenant(self.user_id,
                                                        self.tenant_id)
