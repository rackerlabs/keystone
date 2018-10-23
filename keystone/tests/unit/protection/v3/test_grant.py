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

import uuid

from oslo_serialization import jsonutils
from six.moves import http_client

from keystone.common.policies import credential as cp
from keystone.common import provider_api
import keystone.conf
from keystone.tests.common import auth as common_auth
from keystone.tests import unit
from keystone.tests.unit import base_classes
from keystone.tests.unit import ksfixtures
from keystone.tests.unit.ksfixtures import temporaryfile

CONF = keystone.conf.CONF
PROVIDERS = provider_api.ProviderAPIs

class SystemReaderTests(base_classes.TestCaseWithBootstrap,
                        common_auth.AuthTestMixin):

    def setUp(self):
        super(SystemReaderTests, self).setUp()
        self.loadapp()
        self.useFixture(ksfixtures.Policy(self.config_fixture))
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        project = unit.new_project_ref(
            domain_id=CONF.identity.default_domain_id
        )
        self.project_id = PROVIDERS.resource_api.create_project(
            project['id'], project)['id']

        system_reader = unit.new_user_ref(
            domain_id=CONF.identity.default_domain_id,
        )
        self.user_id = PROVIDERS.identity_api.create_user(
            system_reader
        )['id']

        PROVIDERS.assignment_api.create_system_grant_for_user(
            self.user_id, self.bootstrapper.reader_role_id)

        group_reader = unit.new_group_ref(
            domain_id=CONF.identity.default_domain_id
        )
        self.group_id = PROVIDERS.identity_api.create_group(
            group_reader
        )['id']

        PROVIDERS.identity_api.add_user_to_group(
            user_id=self.user_id, group_id=self.group_id)

        PROVIDERS.assignment_api.create_grant(
            self.bootstrapper.reader_role_id,
            group_id=self.group_id,
            project_id=self.project_id
        )

        auth = self.build_authentication_request(
            user_id=self.user_id, password=system_reader['password'],
            system=True
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}

    def test_user_can_check_grant_for_project(self):

        with self.test_client() as c:
            # GET / HEAD / v3 / projects / {project_id / groups / {group_id} / roles / {role_id}

            c.get("/v3/projects/%s/groups/%s/roles/%s" % (
                self.project_id, self.group_id, self.bootstrapper.reader_role_id),
                  headers=self.headers,
                  expected_status_code=http_client.NO_CONTENT)
            