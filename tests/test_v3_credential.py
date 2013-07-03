# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack LLC
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

from keystone import credential

import test_v3


class CredentialTestCase(test_v3.RestfulTestCase):
    """Test credential CRUD."""
    def setUp(self):

        super(CredentialTestCase, self).setUp()

        credential_data = self.new_credential_ref(
            user_id=self.user['id'],
            project_id=self.project_id)
        self.credential = credential.Credential.create(**credential_data)

    def test_list_credentials(self):
        """Call ``GET /credentials``."""
        r = self.get('/credentials')
        self.assertValidCredentialListResponse(r, ref=self.credential)

    def test_list_credentials_xml(self):
        """Call ``GET /credentials`` (xml data)."""
        r = self.get('/credentials', content_type='xml')
        self.assertValidCredentialListResponse(r, ref=self.credential)

    def test_create_credential(self):
        """Call ``POST /credentials``."""
        credential_data = self.new_credential_ref(user_id=self.user['id'])
        ref = credential.Credential.new(**credential_data)
        r = self.post(
            '/credentials',
            body={'credential': ref})
        self.assertValidCredentialResponse(r, ref)

    def test_get_credential(self):
        """Call ``GET /credentials/{credential_id}``."""
        r = self.get(
            '/credentials/%(credential_id)s' % {
                'credential_id': self.credential.id})
        self.assertValidCredentialResponse(r, self.credential)

    def test_update_credential(self):
        """Call ``PATCH /credentials/{credential_id}``."""
        credential_data = self.new_credential_ref(
            user_id=self.user['id'],
            project_id=self.project_id)
        ref = credential.Credential.new(**credential_data)
        del ref['id']
        print "created cred", self.credential.id
        print "update with", ref
        r = self.patch(
            '/credentials/%(credential_id)s' % {
                'credential_id': self.credential.id},
            body={'credential': ref})
        ref['id'] = self.credential.id
        self.assertValidCredentialResponse(r, ref)

    def test_delete_credential(self):
        """Call ``DELETE /credentials/{credential_id}``."""
        self.delete(
            '/credentials/%(credential_id)s' % {
                'credential_id': self.credential.id})
