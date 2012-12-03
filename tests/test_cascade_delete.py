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

from keystone import config
from keystone import identity
from keystone import test

#from keystone.identity.backends.sql import User

#import test_backend_sql

CONF = config.CONF


class CascadeDeleteTests(test.TestCase):
    def setUp(self):
        super(CascadeDeleteTests, self).setUp()

        # define names
        self.role_name = 'admin'
        self.project_name = 'ProjectA'
        self.domain_name = 'DomainB'

        self.identity_man = identity.Manager()
        self.identity_api = self.identity_man.driver

    def tearDown(self):
        # Delete the project
#        project = self.identity_api.get_project_by_name(self.project_name,
#                                                        self.domain_id)
#        self.identity_api.delete_project(project['id'])
        super(CascadeDeleteTests, self).tearDown()

    def get_role_by_name(self, role_name):
        roles = self.identity_api.list_roles()
        for role in roles:
            if(role['name'] == role_name):
                return role['id']

    def create_role (self, role_id, role_name):
        role = {'id': role_id,
                'name': role_name}
        try:
            self.identity_api.create_role(role_id, role)
        except:
            # retrieve the role
            role_id = self.get_role_by_name(role_name)
        return role_id

    def create_objects(self):
        # create the domain
        self.domain_id = uuid.uuid4().hex
        domain = {
            'id': self.domain_id,
            'name': self.domain_name}
        try:
            self.identity_api.create_domain(self.domain_id, domain)
        except:
            domain = self.identity_api.get_domain_by_name(self.domain_name)
            self.domain_id = domain['id']

        # create the project
        self.project_id = uuid.uuid4().hex
        project = {
            'id': self.project_id,
            'name': self.project_name,
            'domain_id': self.domain_id}
        try:
            self.identity_api.create_project(self.project_id, project)
        except:
            project = self.identity_api.get_project_by_name(self.project_name,
                                                            self.domain_id)
            self.project_id = project['id']

        # create the user
        user_name = "FooY"
        self.user_id = uuid.uuid4().hex
        user = {'id': self.user_id,
                'name': user_name,
                'password': 'password',
                'domain_id': self.domain_id}
        try:
            self.identity_api.create_user(self.user_id, user)
        except:
            user = self.identity_api.get_user_by_name(user_name,
                                                      self.domain_id)
            self.user_id = user['id']

        # create default role
        # self.create_role (config.CONF.member_role_id, "default")

        # add user to project
        self.identity_api.add_user_to_project(self.project_id, self.user_id)

        # create the role
        self.role_id = self.create_role (uuid.uuid4().hex, self.role_name)

        # associate user to a role
        try:
            self.identity_api.add_role_to_user_and_project(self.user_id,
                                                           self.project_id,
                                                           self.role_id)
        except:
            pass

    def test_delete_role(self):
        self.create_objects()

        self.role_id = self.get_role_by_name(self.role_name)
        api = self.identity_api
        roles = api.get_roles_for_user_and_project(self.user_id,
                                                   self.project_id)
        length = len(roles)
        self.identity_api.delete_role(self.role_id)

        roles = api.get_roles_for_user_and_project(self.user_id,
                                                   self.project_id)

        self.assertEquals(len(roles), length - 1)
