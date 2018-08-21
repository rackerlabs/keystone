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

from six.moves import http_client

from keystone.common import provider_api
import keystone.conf
from keystone.tests import unit
from keystone.tests.unit import test_v3

CONF = keystone.conf.CONF
PROVIDERS = provider_api.ProviderAPIs


class SystemReaderTests(test_v3.RestfulTestCase):

    def setUp(self):
        super(SystemReaderTests, self).setUp()
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        system_reader = unit.new_user_ref(
            domain_id=CONF.identity.default_domain_id
        )
        self.system_reader_id = PROVIDERS.identity_api.create_user(
            system_reader
        )['id']
        PROVIDERS.assignment_api.create_system_grant_for_user(
            self.system_reader_id, self.reader_role_id
        )

        self.auth = self.build_authentication_request(
            user_id=self.system_reader_id, password=system_reader['password'],
            system=True
        )

    def test_user_can_create_credentials_for_themselves(self):
        credential_body = {
            'credential': {
                'blob': uuid.uuid4().hex,
                'user_id': self.system_reader_id,
                'type': uuid.uuid4().hex
            }
        }
        self.post('/credentials', body=credential_body, auth=self.auth)

    def test_user_can_get_a_credential(self):
        credential_body = {
            'credential': {
                'blob': uuid.uuid4().hex,
                'user_id': self.system_reader_id,
                'type': uuid.uuid4().hex
            }
        }
        r = self.post('/credentials', body=credential_body, auth=self.auth)
        credential_id = r.json_body['credential']['id']
        path = '/credentials/%(cred_id)s' % {'cred_id': credential_id}
        self.get(path, auth=self.auth)

    def test_user_can_list_their_credentials(self):
        expected = []
        for _ in range(2):
            credential_body = {
                'credential': {
                    'blob': uuid.uuid4().hex,
                    'user_id': self.system_reader_id,
                    'type': uuid.uuid4().hex
                }
            }
            r = self.post('/credentials', body=credential_body, auth=self.auth)
            expected.append(r.json_body['credential'])

        r = self.get('/credentials', auth=self.auth)
        for credential in expected:
            self.assertIn(credential, r.json_body['credentials'])

    def test_user_can_update_their_own_credential(self):
        credential_body = {
            'credential': {
                'blob': uuid.uuid4().hex,
                'user_id': self.system_reader_id,
                'type': uuid.uuid4().hex
            }
        }
        r = self.post('/credentials', body=credential_body, auth=self.auth)
        credential_id = r.json_body['credential']['id']

        update = {'credential': {'blob': uuid.uuid4().hex}}

        path = '/credentials/%(cred_id)s' % {'cred_id': credential_id}
        self.patch(path, body=update, auth=self.auth)

    def test_user_can_delete_credentials_for_themselves(self):
        credential_body = {
            'credential': {
                'blob': uuid.uuid4().hex,
                'user_id': self.system_reader_id,
                'type': uuid.uuid4().hex
            }
        }
        r = self.post('/credentials', body=credential_body, auth=self.auth)
        credential_id = r.json_body['credential']['id']

        path = '/credentials/%(cred_id)s' % {'cred_id': credential_id}
        self.delete(path, auth=self.auth)

    def test_user_cannot_create_credentials_for_others(self):
        user = PROVIDERS.identity_api.create_user(
            unit.new_user_ref(domain_id=CONF.identity.default_domain_id)
        )
        credential_body = {
            'credential': {
                'blob': uuid.uuid4().hex,
                'user_id': user['id'],
                'type': uuid.uuid4().hex
            }
        }
        self.post(
            '/credentials', body=credential_body, auth=self.auth,
            expected_status=http_client.FORBIDDEN
        )

    def test_user_cannot_list_credentials_for_others(self):
        pass

    def test_user_cannot_update_credentials_for_others(self):
        pass

    def test_user_cannot_delete_credentials_for_others(self):
        pass


class SystemMemberTests(test_v3.RestfulTestCase):

    def setUp(self):
        super(SystemMemberTests, self).setUp()
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        system_member = unit.new_user_ref(
            domain_id=CONF.identity.default_domain_id
        )
        self.system_member_id = PROVIDERS.identity_api.create_user(
            system_member
        )['id']
        PROVIDERS.assignment_api.create_system_grant_for_user(
            self.system_member_id, self.member_role_id
        )

        self.auth = self.build_authentication_request(
            user_id=self.system_member_id, password=system_member['password'],
            system=True
        )

    def test_user_can_create_credentials_for_themselves(self):
        credential_body = {
            'credential': {
                'blob': uuid.uuid4().hex,
                'user_id': self.system_member_id,
                'type': uuid.uuid4().hex
            }
        }
        self.post('/credentials', body=credential_body, auth=self.auth)

    def test_user_can_get_a_credential(self):
        pass

    def test_user_can_list_their_credentials(self):
        pass

    def test_user_can_update_their_own_credential(self):
        pass

    def test_user_can_delete_credentials_for_themselves(self):
        pass

    def test_user_can_update_credentials_for_others(self):
        pass

    def test_user_cannot_delete_credentials_for_others(self):
        pass


class SystemAdminTests(test_v3.RestfulTestCase):

    def setUp(self):
        super(SystemAdminTests, self).setUp()
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        self.auth = self.build_authentication_request(
            user_id=self.user_id, password=self.user['password'], system=True
        )

    def test_user_can_create_credentials_for_themselves(self):
        credential_body = {
            'credential': {
                'blob': uuid.uuid4().hex,
                'user_id': self.user_id,
                'type': uuid.uuid4().hex
            }
        }
        self.post('/credentials', body=credential_body, auth=self.auth)

    def test_user_can_get_a_credential(self):
        pass

    def test_user_can_list_their_credentials(self):
        pass

    def test_user_can_update_their_own_credential(self):
        pass

    def test_user_can_delete_credentials_for_themselves(self):
        pass

    def test_user_can_update_credentials_for_others(self):
        pass

    def test_user_can_delete_credentials_for_others(self):
        pass


class ProjectReaderTests(test_v3.RestfulTestCase):

    def setUp(self):
        super(ProjectReaderTests, self).setUp()
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        project_reader = unit.new_user_ref(
            domain_id=CONF.identity.default_domain_id
        )
        self.project_reader_id = PROVIDERS.identity_api.create_user(
            project_reader
        )['id']
        PROVIDERS.assignment_api.create_grant(
            self.reader_role_id, user_id=self.project_reader_id,
            project_id=self.project_id
        )

        self.auth = self.build_authentication_request(
            user_id=self.project_reader_id,
            password=project_reader['password'],
            project_id=self.project_id
        )

    def test_user_can_create_credentials_for_themselves(self):
        credential_body = {
            'credential': {
                'blob': uuid.uuid4().hex,
                'user_id': self.project_reader_id,
                'type': uuid.uuid4().hex
            }
        }
        self.post('/credentials', body=credential_body, auth=self.auth)

    def test_user_can_get_a_credential(self):
        pass

    def test_user_can_list_their_credentials(self):
        pass

    def test_user_can_update_their_own_credential(self):
        pass

    def test_user_can_delete_credentials_for_themselves(self):
        pass

    def test_user_cannot_update_credentials_for_others(self):
        pass

    def test_user_cannot_create_credentials_for_others(self):
        pass

    def test_user_cannot_delete_credentials_for_others(self):
        pass


class ProjectMemberTests(ProjectReaderTests):
        pass


class ProjectAdminTests(ProjectReaderTests):
        pass
