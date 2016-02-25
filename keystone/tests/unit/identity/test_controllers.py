# Copyright 2016 IBM Corp.
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

from oslo_config import cfg

from keystone import exception
from keystone.identity import controllers
from keystone.tests import unit
from keystone.tests.unit.ksfixtures import database


CONF = cfg.CONF

_ADMIN_CONTEXT = {'is_admin': True}


class UserTestCaseNoFixtures(unit.TestCase):

    def setUp(self):
        super(UserTestCaseNoFixtures, self).setUp()
        self.useFixture(database.Database())
        self.load_backends()
        self.user_controller = controllers.User()

    def test_create_user_no_default_domain(self):
        # When a user is created using the v2 controller and there's no default
        # domain, it doesn't fail with can't find domain (a default domain is
        # created)

        # First make sure there's no default domain.
        self.assertRaises(
            exception.DomainNotFound,
            self.resource_api.get_domain, CONF.identity.default_domain_id)

        user = {'name': uuid.uuid4().hex}
        self.user_controller.create_user(_ADMIN_CONTEXT, user)
        # If the above doesn't fail then this is successful.
