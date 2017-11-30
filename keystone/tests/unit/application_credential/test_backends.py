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

from keystone.common import provider_api
import keystone.conf


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
        app_cred_api = PROVIDERS.application_credential_api
        resp = app_cred_api.create_application_credential(app_cred)
        self.assertDictEqual(app_cred, resp)

    def test_create_duplicate_application_credential(self):
        # Ensure a user can't create two application credentials with the same
        # name
        pass

    def test_get_application_credential(self):
        pass

    def test_get_application_credential_not_found(self):
        pass

    def test_list_application_credentials(self):
        pass

    def test_delete_application_credential(self):
        pass

    def test_delete_application_credentials_for_user(self):
        pass

    def test_delete_application_credentails_for_user_on_project(self):
        pass

    def test_authenticate(self):
        pass

    def test_authenticate_not_found(self):
        pass

    def test_authenticate_expired(self):
        pass

    def test_authenticate_bad_secret(self):
        pass
