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

import datetime
import uuid

from keystone.common import driver_hints
from keystone.common import provider_api
import keystone.conf
from keystone import exception


CONF = keystone.conf.CONF
PROVIDERS = provider_api.ProviderAPIs


class ApplicationCredentialTests(object):

    def create_application_credential(self, user_id, project_id, name=None,
                                      expires=None):
        if not name:
            name = uuid.uuid4().hex
        if not expires:
            expires = datetime.datetime.utcnow() + datetime.timedelta(days=365)
        app_cred_data = {
            'id': uuid.uuid4().hex,
            'name': name,
            'description': uuid.uuid4().hex,
            'user_id': user_id,
            'project_id': project_id,
            'expires_at': expires,
            'roles': [
                {'id': self.role__member_['id']},
            ],
            'secret': uuid.uuid4().hex,
        }
        return app_cred_data

    def test_create_application_credential(self):
        app_cred = self.create_application_credential(self.user_foo['id'],
                                                      self.tenant_bar['id'])
        resp = self.app_cred_api.create_application_credential(app_cred)
        self.assertDictEqual(app_cred, resp)

    def test_create_duplicate_application_credential(self):
        # Ensure a user can't create two application credentials with the same
        # name
        app_cred = self.create_application_credential(self.user_foo['id'],
                                                      self.tenant_bar['id'])
        name = app_cred['name']
        self.app_cred_api.create_application_credential(app_cred)
        app_cred = self.create_application_credential(self.user_foo['id'],
                                                      self.tenant_bar['id'],
                                                      name=name)
        self.assertRaises(exception.Conflict,
                          self.app_cred_api.create_application_credential,
                          app_cred)

    def test_create_application_credential_require_role_assignments(self):
        # Ensure a user can't create an application credential for a project
        # they don't have a role assignment on
        app_cred = self.create_application_credential(self.user_foo['id'],
                                                      self.tenant_baz['id'])
        self.assertRaises(exception.RoleNotFound,
                          self.app_cred_api.create_application_credential,
                          app_cred)

    def test_get_application_credential(self):
        app_cred = self.create_application_credential(self.user_foo['id'],
                                                      self.tenant_bar['id'])
        create_resp = self.app_cred_api.create_application_credential(app_cred)
        app_cred_id = create_resp['id']
        get_resp = self.app_cred_api.get_application_credential(app_cred_id)
        create_resp.pop('secret')
        self.assertDictEqual(create_resp, get_resp)

    def test_get_application_credential_not_found(self):
        self.assertRaises(exception.ApplicationCredentialNotFound,
                          self.app_cred_api.get_application_credential,
                          uuid.uuid4().hex)

    def test_list_application_credentials(self):
        app_cred_1 = self.create_application_credential(self.user_foo['id'],
                                                        self.tenant_bar['id'],
                                                        name='app1')
        app_cred_2 = self.create_application_credential(self.user_foo['id'],
                                                        self.tenant_bar['id'],
                                                        name='app2')
        app_cred_3 = self.create_application_credential(self.user_two['id'],
                                                        self.tenant_baz['id'],
                                                        name='app3')
        resp1 = self.app_cred_api.create_application_credential(app_cred_1)
        resp2 = self.app_cred_api.create_application_credential(app_cred_2)
        resp3 = self.app_cred_api.create_application_credential(app_cred_3)
        hints = driver_hints.Hints()
        resp = self.app_cred_api.list_application_credentials(
            self.user_foo['id'], hints)
        resp_ids = [ac['id'] for ac in resp]
        self.assertIn(resp1['id'], resp_ids)
        self.assertIn(resp2['id'], resp_ids)
        self.assertNotIn(resp3['id'], resp_ids)
        for ac in resp:
            self.assertNotIn('secret_hash', ac)

    def _list_ids(self, user):
        hints = driver_hints.Hints()
        resp = self.app_cred_api.list_application_credentials(user['id'],
                                                              hints)
        return [ac['id'] for ac in resp]

    def test_delete_application_credential(self):
        app_cred = self.create_application_credential(self.user_foo['id'],
                                                      self.tenant_bar['id'])
        self.app_cred_api.create_application_credential(app_cred)
        self.assertIn(app_cred['id'], self._list_ids(self.user_foo))
        self.app_cred_api.delete_application_credential(app_cred['id'])
        self.assertNotIn(app_cred['id'], self._list_ids(self.user_foo))

    def test_delete_application_credential_not_found(self):
        self.assertRaises(exception.ApplicationCredentialNotFound,
                          self.app_cred_api.delete_application_credential,
                          uuid.uuid4().hex)

    def test_delete_application_credentials_for_user(self):
        app_cred_1 = self.create_application_credential(self.user_foo['id'],
                                                        self.tenant_bar['id'],
                                                        name='app1')
        app_cred_2 = self.create_application_credential(self.user_foo['id'],
                                                        self.tenant_bar['id'],
                                                        name='app2')
        self.app_cred_api.create_application_credential(app_cred_1)
        self.app_cred_api.create_application_credential(app_cred_2)
        self.assertIn(app_cred_1['id'], self._list_ids(self.user_foo))
        self.assertIn(app_cred_2['id'], self._list_ids(self.user_foo))
        self.app_cred_api.delete_application_credentials_for_user(
            self.user_foo['id'])
        hints = driver_hints.Hints()
        self.assertListEqual(
            [], self.app_cred_api.list_application_credentials(
                self.user_foo['id'], hints))

    def test_delete_application_credentials_for_user_on_project(self):
        app_cred_proj_A_1 = self.create_application_credential(
            self.user_foo['id'], self.tenant_bar['id'], name='app1')
        app_cred_proj_A_2 = self.create_application_credential(
            self.user_foo['id'], self.tenant_bar['id'], name='app2')
        app_cred_proj_B = self.create_application_credential(
            self.user_foo['id'], self.tenant_baz['id'], name='app3')
        PROVIDERS.assignment_api.add_role_to_user_and_project(
            tenant_id=self.tenant_baz['id'],
            user_id=self.user_foo['id'],
            role_id=self.role__member_['id'])
        self.app_cred_api.create_application_credential(app_cred_proj_A_1)
        self.app_cred_api.create_application_credential(app_cred_proj_A_2)
        self.app_cred_api.create_application_credential(app_cred_proj_B)
        self.assertIn(app_cred_proj_A_1['id'], self._list_ids(self.user_foo))
        self.assertIn(app_cred_proj_A_2['id'], self._list_ids(self.user_foo))
        self.assertIn(app_cred_proj_B['id'], self._list_ids(self.user_foo))
        self.app_cred_api.delete_application_credentials_for_user_on_project(
            self.user_foo['id'], self.tenant_bar['id'])
        self.assertNotIn(app_cred_proj_A_1['id'],
                         self._list_ids(self.user_foo))
        self.assertNotIn(app_cred_proj_A_2['id'],
                         self._list_ids(self.user_foo))
        self.assertIn(app_cred_proj_B['id'], self._list_ids(self.user_foo))

    def test_authenticate(self):
        app_cred = self.create_application_credential(self.user_foo['id'],
                                                      self.tenant_bar['id'])
        resp = self.app_cred_api.create_application_credential(app_cred)
        secret = resp['secret']
        self.app_cred_api.authenticate(
            self.make_request(), resp['id'], resp['secret'])

    def test_authenticate_not_found(self):
        self.assertRaises(AssertionError,
                          self.app_cred_api.authenticate,
                          self.make_request(),
                          uuid.uuid4().hex,
                          uuid.uuid4().hex)

    def test_authenticate_expired(self):
        yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        app_cred = self.create_application_credential(self.user_foo['id'],
                                                      self.tenant_bar['id'],
                                                      expires=yesterday)
        resp = self.app_cred_api.create_application_credential(app_cred)
        self.assertRaises(AssertionError,
                          self.app_cred_api.authenticate,
                          self.make_request(),
                          resp['id'],
                          resp['secret'])

    def test_authenticate_bad_secret(self):
        app_cred = self.create_application_credential(self.user_foo['id'],
                                                      self.tenant_bar['id'])
        resp = self.app_cred_api.create_application_credential(app_cred)
        badpass = 'badpass'
        self.assertNotEqual(badpass, resp['secret'])
        self.assertRaises(AssertionError,
                          self.app_cred_api.authenticate,
                          self.make_request(),
                          resp['id'],
                          badpass)
