# Copyright (c) 2010-2011 OpenStack, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import unittest2 as unittest
import httplib2
import json
from lxml import etree
import uuid
from keystone.test.unit import common


class UserTest(common.FunctionalTest):

    def setUp(self, *args, **kwargs):
        super(UserTest, self).setUp(*args, **kwargs)

        self.tenant_name2 = common.unique_str()
        self.tenant_id2 = common.create_tenant(self.tenant_name2,
            self.admin_token)

    def tearDown(self, *args, **kwargs):
        common.delete_tenant(self.tenant_id2, self.admin_token)

        super(UserTest, self).tearDown(*args, **kwargs)


class CreateUserTest(UserTest):

    def test_a_user_create_json(self):
        common.delete_user(self.user_id, self.admin_token)
        resp, content = common.create_user_json(self.tenant_id, self.user_name,
            self.admin_token)
        self.assertStatusCode(201, resp, content)

    def test_a_user_with_no_tenant(self):
        common.delete_user(self.user_id, self.admin_token)
        resp, content = common.create_user_json(None, self.user_name,
            self.admin_token)
        self.assertStatusCode(201, resp, content)

    def test_a_user_create_xml(self):
        common.delete_user_xml(self.user_id, self.admin_token)
        resp, content = common.create_user_xml(self.tenant_id, self.user_name,
            self.admin_token)
        self.assertStatusCode(201, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_a_user_create_json_disabled_tenant(self):
        resp, content = common.create_user_json('0000', self.user_name,
            self.admin_token)
        self.assertStatusCode(403, resp, content)

    def test_a_user_create_json_disabled_tenant_xml(self):
        resp, content = common.create_user_xml('0000', self.user_name,
            self.admin_token)
        self.assertStatusCode(403, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_a_user_create_again_json(self):
        resp, content = common.create_user_json(self.tenant_id, self.user_name,
            self.admin_token)
        self.assertStatusCode(409, resp, content)

    def test_a_user_create_again_xml(self):
        resp, content = common.create_user_xml(self.tenant_id, self.user_name,
            self.admin_token)
        self.assertStatusCode(409, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_create_users_with_duplicate_emails(self):
        email = 'using-this-email-twice-json@openstack.org'
        resp, content = common.create_user_json(self.tenant_id, str(uuid.uuid4()),
            self.admin_token, email)
        self.assertStatusCode(201, resp, content)
        resp, content = common.create_user_json(self.tenant_id, str(uuid.uuid4()),
            self.admin_token, email)
        self.assertStatusCode(409, resp, content)

    def test_create_users_with_duplicate_emails_xml(self):
        email = 'using-this-email-twice-xml@openstack.org'
        resp, content = common.create_user_xml(self.tenant_id, str(uuid.uuid4()),
            self.admin_token, email)
        self.assertStatusCode(201, resp, content)
        self.assertContentType('application/xml', resp, content)
        resp, content = common.create_user_xml(self.tenant_id, str(uuid.uuid4()),
            self.admin_token, email)
        self.assertStatusCode(409, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_a_user_create_empty_password_json(self):
        resp, content = common.create_user_json(self.tenant_id, str(uuid.uuid4()),
            self.admin_token, self.email, '')
        self.assertStatusCode(400, resp, content)

    def test_a_user_create_empty_password_xml(self):
        resp, content = common.create_user_xml(self.tenant_id, str(uuid.uuid4()),
            self.admin_token, self.email, '')
        self.assertStatusCode(400, resp, content)

    def test_a_user_create_empty_username_json(self):
        resp, content = common.create_user_json(self.tenant_id, '',
            self.admin_token, self.email)
        self.assertStatusCode(400, resp, content)

    def test_a_user_create_empty_username_xml(self):
        resp, content = common.create_user_xml(self.tenant_id, '', self.admin_token,
            self.email)
        self.assertStatusCode(400, resp, content)

    def test_a_user_create_expired_token(self):
        resp, content = common.create_user_json(self.tenant_id, str(uuid.uuid4()),
            self.exp_admin_token)
        self.assertStatusCode(403, resp, content)

    def test_a_user_create_expired_token_xml(self):
        username = str(uuid.uuid4())
        resp, content = common.create_user_xml(self.tenant_id, username,
            self.exp_admin_token)
        self.assertStatusCode(403, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_a_user_create_disabled_token(self):
        username = str(uuid.uuid4())
        resp, content = common.create_user_json(self.tenant_id, username,
            self.disabled_token)
        self.assertStatusCode(403, resp, content)

    def test_a_user_create_disabled_token_xml(self):
        username = str(uuid.uuid4())
        resp, content = common.create_user_xml(self.tenant_id, username,
            self.disabled_token)
        self.assertStatusCode(403, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_a_user_create_missing_token(self):
        username = str(uuid.uuid4())
        resp, content = common.create_user_json(self.tenant_id, username,
            self.missing_token)
        self.assertStatusCode(401, resp, content)

    def test_a_user_create_missing_token_xml(self):
        username = str(uuid.uuid4())
        resp, content = common.create_user_xml(self.tenant_id, username,
            self.missing_token)
        self.assertStatusCode(401, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_a_user_create_invalid_token(self):
        resp, content = common.create_user_json(self.tenant_id, str(uuid.uuid4()),
            self.invalid_token)
        self.assertStatusCode(404, resp, content)

    def test_a_user_create_invalid_token_xml(self):
        resp, content = common.create_user_xml(self.tenant_id, str(uuid.uuid4()),
            self.invalid_token)
        self.assertStatusCode(404, resp, content)
        self.assertContentType('application/xml', resp, content)


class GetUserTest(UserTest):

    def test_a_user_get(self):
        resp, content = common.user_get_json(self.user_id, self.admin_token)
        self.assertStatusCode(200, resp, content)

    def test_a_user_get_xml(self):
        resp, content = common.user_get_xml(self.user_id, self.admin_token)
        self.assertStatusCode(200, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_a_user_get_expired_token(self):
        resp, content = common.user_get_json(self.user_id, self.exp_admin_token)
        self.assertStatusCode(403, resp, content)

    def test_a_user_get_expired_token_xml(self):
        resp, content = common.user_get_xml(self.user_id, self.exp_admin_token)
        self.assertStatusCode(403, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_a_user_get_disabled_token(self):
        resp, content = common.user_get_json(self.user_id, self.disabled_token)
        self.assertStatusCode(403, resp, content)

    def test_a_user_get_disabled_token_xml(self):
        resp, content = common.user_get_xml(self.user_id, self.disabled_token)
        self.assertStatusCode(403, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_a_user_get_missing_token(self):
        resp, content = common.user_get_json(self.user_id, self.missing_token)
        self.assertStatusCode(401, resp, content)

    def test_a_user_get_missing_token_xml(self):
        resp, content = common.user_get_xml(self.user_id, self.missing_token)
        self.assertStatusCode(401, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_a_user_get_invalid_token(self):
        resp, content = common.user_get_json(self.user_id, self.invalid_token)
        self.assertStatusCode(404, resp, content)

    def test_a_user_get_invalid_token_xml(self):
        resp, content = common.user_get_xml(self.user_id, self.invalid_token)
        self.assertStatusCode(404, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_a_user_get_disabled_user(self):
        resp, content = common.user_get_json(self.disabled_user_id,
            self.admin_token)
        self.assertStatusCode(200, resp, content)

    def test_a_user_get_disabled_user_xml(self):
        resp, content = common.user_get_xml(self.disabled_user_id,
            self.admin_token)
        self.assertStatusCode(200, resp, content)
        self.assertContentType('application/xml', resp, content)


class DeleteUserTest(UserTest):

    def test_a_user_delete(self):
        resp = common.delete_user(self.user_id, self.admin_token)
        self.assertStatusCode(204, resp, None)

    def test_a_user_delete_xml(self):
        resp = common.delete_user_xml(self.user_id, self.admin_token)
        self.assertStatusCode(204, resp, None)

    def test_a_user_delete_expired_token(self):
        resp = common.delete_user(self.user_id, self.exp_admin_token)
        self.assertStatusCode(403, resp, None)

    def test_a_user_delete_expired_token_xml(self):
        resp = common.delete_user_xml(self.user_id, self.exp_admin_token)
        self.assertStatusCode(403, resp, None)
        self.assertContentType('application/xml', resp, None)

    def test_a_user_delete_missing_token(self):
        resp = common.delete_user(self.user_id, self.missing_token)
        self.assertStatusCode(401, resp, None)

    def test_a_user_delete_missing_token_xml(self):
        resp = common.delete_user_xml(self.user_id, self.missing_token)
        self.assertStatusCode(401, resp, None)
        self.assertContentType('application/xml', resp, None)

    def test_a_user_delete_invalid_token(self):
        resp = common.delete_user(self.user_id, self.invalid_token)
        self.assertStatusCode(404, resp, None)

    def test_a_user_delete_invalid_token_xml(self):
        resp = common.delete_user_xml(self.user_id, self.invalid_token)
        self.assertStatusCode(404, resp, None)
        self.assertContentType('application/xml', resp, None)


class GetAllUsersTest(UserTest):
    def test_users_get(self):
        resp, content = common.users_get_all_json(self.admin_token)
        self.assertStatusCode(200, resp, content)

    def test_users_get_xml(self):
        resp, content = common.users_get_all_xml(self.admin_token)
        self.assertStatusCode(200, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_users_get_expired_token(self):
        resp, content = common.users_get_all_json(self.exp_admin_token)
        self.assertStatusCode(403, resp, content)

    def test_users_get_expired_token_xml(self):
        resp, content = common.users_get_all_xml(self.exp_admin_token)
        self.assertStatusCode(403, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_users_get_disabled_token(self):
        resp, content = common.users_get_all_json(self.disabled_token)
        self.assertStatusCode(403, resp, content)

    def test_users_get_disabled_token_xml(self):
        resp, content = common.users_get_all_xml(self.disabled_token)
        self.assertStatusCode(403, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_users_get_missing_token(self):
        resp, content = common.users_get_all_json(self.missing_token)
        self.assertStatusCode(401, resp, content)

    def test_users_get_missing_token_xml(self):
        resp, content = common.users_get_all_xml(self.missing_token)
        self.assertStatusCode(401, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_users_get_invalid_token(self):
        resp, content = common.users_get_all_json(self.invalid_token)
        self.assertStatusCode(404, resp, content)

    def test_users_get_invalid_token_xml(self):
        resp, content = common.users_get_all_xml(self.invalid_token)
        self.assertStatusCode(404, resp, content)
        self.assertContentType('application/xml', resp, content)


class GetUsersTest(UserTest):

    def test_users_get(self):
        resp, content = common.users_get_json(self.user_id, self.admin_token)
        self.assertStatusCode(200, resp, content)

    def test_users_get_xml(self):
        resp, content = common.users_get_xml(self.user_id, self.admin_token)
        self.assertStatusCode(200, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_users_get_expired_token(self):
        resp, content = common.users_get_json(self.user_id, self.exp_admin_token)
        self.assertStatusCode(403, resp, content)

    def test_users_get_expired_token_xml(self):
        resp, content = common.users_get_xml(self.user_id,
            self.exp_admin_token)
        self.assertStatusCode(403, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_users_get_disabled_token(self):
        resp, content = common.users_get_json(self.user_id, self.disabled_token)
        self.assertStatusCode(403, resp, content)

    def test_users_get_disabled_token_xml(self):
        resp, content = common.users_get_xml(self.user_id, self.disabled_token)
        self.assertStatusCode(403, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_users_get_missing_token(self):
        resp, content = common.users_get_json(self.user_id, self.missing_token)
        self.assertStatusCode(401, resp, content)

    def test_users_get_missing_token_xml(self):
        resp, content = common.users_get_xml(self.user_id, self.missing_token)
        self.assertStatusCode(401, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_users_get_invalid_token(self):
        resp, content = common.users_get_json(self.user_id, self.invalid_token)
        self.assertStatusCode(404, resp, content)

    def test_users_get_invalid_token_xml(self):
        resp, content = common.users_get_xml(self.user_id, self.invalid_token)
        self.assertStatusCode(404, resp, content)
        self.assertContentType('application/xml', resp, content)


class UpdateUserTest(UserTest):

    def test_user_update(self):
        resp, content = common.user_update_json(self.admin_token, self.user_id)
        self.assertStatusCode(200, resp, content)
        content = json.loads(content)
        self.assertEqual('updatedjoeuser@openstack.org',
            content['user']['email'])

    def test_user_update_xml(self):
        resp, content = common.user_update_xml(self.admin_token, self.user_id)
        self.assertStatusCode(200, resp, content)
        self.assertContentType('application/xml', resp, content)
        content = etree.fromstring(content)
        self.assertEqual('updatedjoeuser@openstack.org', content.get("email"))

    def test_user_update_user_disabled(self):
        common.user_set_enabled(self.admin_token, self.user_id, enabled=False)
        resp, content = common.user_update_json(self.admin_token, self.user_id)
        self.assertStatusCode(200, resp, content)

    def test_user_update_user_disabled_xml(self):
        common.user_set_enabled(self.admin_token, self.user_id, enabled=False)
        resp, content = common.user_update_xml(self.admin_token, self.user_id)
        self.assertStatusCode(200, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_user_update_bad_request_json(self):
        h = httplib2.Http(".cache")
        url = '%susers/%s' % (common.URL_V2, self.user_id)
        data = '{"user_bad": { "bad": "updatedjoeuser@openstack.org"}}'
        resp, content = h.request(url, "PUT", body=data, headers={
            "Content-Type": "application/json",
            "X-Auth-Token": self.admin_token})
        self.assertStatusCode(400, resp, content)

    def test_user_update_bad_request_xml(self):
        h = httplib2.Http(".cache")
        url = '%susers/%s' % (common.URL_V2, self.user_id)
        data = '<?xml version="1.0" encoding="UTF-8"?> \
                user xmlns="http://docs.openstack.org/identity/api/v2.0" \
                email="updatedjoeuser@openstack.org" />'
        resp, content = h.request(url, "PUT", body=data, headers={
            "Content-Type": "application/xml",
            "X-Auth-Token": self.admin_token,
            "ACCEPT": "application/xml"})
        self.assertStatusCode(400, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_user_update_expired_token(self):
        resp, content = common.user_update_json(self.exp_admin_token,
            self.user_id)
        self.assertStatusCode(403, resp, content)

    def test_user_update_expired_token_xml(self):
        resp, content = common.user_update_xml(self.exp_admin_token,
            self.user_id)
        self.assertStatusCode(403, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_user_update_disabled_token(self):
        resp, content = common.user_update_json(self.disabled_token,
            self.user_id)
        self.assertStatusCode(403, resp, content)

    def test_user_update_disabled_token_xml(self):
        resp, content = common.user_update_xml(self.disabled_token,
            self.user_id)
        self.assertStatusCode(403, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_user_update_invalid_token(self):
        resp, content = common.user_update_json(self.invalid_token,
            self.user_id)
        self.assertStatusCode(404, resp, content)

    def test_user_update_invalid_token_xml(self):
        resp, content = common.user_update_xml(self.invalid_token, self.user_id)
        self.assertStatusCode(404, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_user_update_missing_token(self):
        resp, content = common.user_update_json(self.missing_token,
            self.user_id)
        self.assertStatusCode(401, resp, content)

    def test_user_update_missing_token_xml(self):
        resp, content = common.user_update_xml(self.missing_token, self.user_id)
        self.assertStatusCode(401, resp, content)
        self.assertContentType('application/xml', resp, content)


class TestUpdateConflict(UserTest):
    user_id2 = None
    username2 = common.unique_str()
    email2 = username2 + '@openstack.org'

    def setUp(self, *args, **kwargs):
        super(TestUpdateConflict, self).setUp(*args, **kwargs)
        self.user_id2 = common.create_user(self.tenant_id,
            self.user_name2, self.admin_token, self.email2,
            self.password)

    def tearDown(self, *args, **kwargs):
        common.delete_user(self.user_id2, self.admin_token)
        super(TestUpdateConflict, self).tearDown(*args, **kwargs)

    def test_user_update_email_conflict_json(self):
        """Replace the second user's email with that of the first"""
        resp, content = common.user_update_json(self.admin_token,
            self.second_user_id, self.first_email)
        self.assertStatusCode(409, resp, content)
        self.assertContentType('application/json', resp, content)

    def test_user_update_email_conflict_xml(self):
        """Replace the second user's email with that of the first"""
        resp, content = common.user_update_xml(self.admin_token,
            self.second_user_id, self.first_email)
        self.assertStatusCode(409, resp, content)
        self.assertContentType('application/xml', resp, content)


class SetPasswordTest(UserTest):

    def test_user_password(self):
        resp, content = common.user_password_json(self.user_id, self.admin_token)
        self.assertStatusCode(200, resp, content)
        content = json.loads(content)
        self.assertEqual('p@ssword', content['user']['password'])

    def test_user_password_xml(self):
        resp, content = common.user_password_xml(self.user_id, self.admin_token)
        self.assertStatusCode(200, resp, content)
        self.assertContentType('application/xml', resp, content)
        content = etree.fromstring(content)
        self.assertEqual('p@ssword', content.get("password"))

    def test_user_password_user_disabled(self):
        resp, content = common.user_password_json(self.disabled_user_id,
            self.admin_token)
        self.assertStatusCode(200, resp, content)

    def test_user_password_user_disabled_xml(self):
        resp, content = common.user_password_xml(self.disabled_user_id,
            self.admin_token)
        self.assertStatusCode(200, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_user_password_bad_request_json(self):
        h = httplib2.Http(".cache")
        url = '%susers/%s/password' % (common.URL_V2, self.user_id)
        data = '{"user_bad": { "password": "p@ssword"}}'
        resp, content = h.request(url, "PUT", body=data, headers={
            "Content-Type": "application/json",
            "X-Auth-Token": self.admin_token})
        self.assertStatusCode(400, resp, content)

    def test_user_password_bad_request_xml(self):
        h = httplib2.Http(".cache")
        url = '%susers/%s/password' % (common.URL_V2, self.user_id)
        data = '<?xml version="1.0" encoding="UTF-8"?> \
                user xmlns="http://docs.openstack.org/identity/api/v2.0" \
                password="p@ssword" />'
        resp, content = h.request(url, "PUT", body=data, headers={
            "Content-Type": "application/xml",
            "X-Auth-Token": self.admin_token,
            "ACCEPT": "application/xml"})
        self.assertStatusCode(400, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_user_password_expired_token(self):
        resp, content = common.user_password_json(self.user_id,
            self.exp_admin_token)
        self.assertStatusCode(403, resp, content)

    def test_user_password_expired_token_xml(self):
        resp, content = common.user_password_xml(self.user_id,
            self.exp_admin_token)
        self.assertStatusCode(403, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_user_password_disabled_token(self):
        resp, content = common.user_password_json(self.user_id,
            self.disabled_token)
        self.assertStatusCode(403, resp, content)

    def test_user_password_disabled_token_xml(self):
        resp, content = common.user_password_xml(self.user_id,
            self.disabled_token)
        self.assertStatusCode(403, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_user_password_invalid_token(self):
        resp, content = common.user_password_json(self.user_id,
            self.invalid_token)
        self.assertStatusCode(404, resp, content)

    def test_user_password_invalid_token_xml(self):
        resp, content = common.user_password_xml(self.user_id,
            self.invalid_token)
        self.assertStatusCode(404, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_user_password_missing_token(self):
        resp, content = common.user_password_json(self.user_id,
            self.missing_token)
        self.assertStatusCode(401, resp, content)

    def test_user_password_missing_token_xml(self):
        resp, content = common.user_password_xml(self.user_id,
            self.missing_token)
        self.assertStatusCode(401, resp, content)
        self.assertContentType('application/xml', resp, content)


class SetEnabledTest(UserTest):

    def test_user_enabled(self):
        resp, content = common.user_enabled_json(self.user_id, self.admin_token)
        self.assertStatusCode(200, resp, content)
        content = json.loads(content)
        self.assertEqual(True, content['user']['enabled'])

    def test_user_enabled_xml(self):
        resp, content = common.user_enabled_xml(self.user_id, self.admin_token)
        self.assertStatusCode(200, resp, content)
        self.assertContentType('application/xml', resp, content)
        content = etree.fromstring(content)
        self.assertEqual('true', content.get("enabled"))

    def test_user_enabled_bad_request_json(self):
        h = httplib2.Http(".cache")
        url = '%susers/%s/enabled' % (common.URL_V2, self.user_id)
        data = '{"user_bad": { "enabled": true}}'
        resp, content = h.request(url, "PUT", body=data, headers={
            "Content-Type": "application/json",
            "X-Auth-Token": self.admin_token})
        self.assertStatusCode(400, resp, content)

    def test_user_enabled_bad_request_xml(self):
        h = httplib2.Http(".cache")
        url = '%susers/%s/enabled' % (common.URL_V2, self.user_id)
        data = '<?xml version="1.0" encoding="UTF-8"?> \
                user xmlns="http://docs.openstack.org/identity/api/v2.0" \
                enabled="true" />'
        resp, content = h.request(url, "PUT", body=data, headers={
            "Content-Type": "application/xml",
            "X-Auth-Token": self.admin_token,
            "ACCEPT": "application/xml"})
        self.assertStatusCode(400, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_user_enabled_expired_token(self):
        resp, content = common.user_enabled_json(self.user_id,
            self.exp_admin_token)
        self.assertStatusCode(403, resp, content)

    def test_user_enabled_expired_token_xml(self):
        resp, content = common.user_enabled_xml(self.user_id,
            self.exp_admin_token)
        self.assertStatusCode(403, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_user_enabled_disabled_token(self):
        resp, content = common.user_enabled_json(self.user_id,
            self.disabled_token)
        self.assertStatusCode(403, resp, content)

    def test_user_enabled_disabled_token_xml(self):
        resp, content = common.user_enabled_xml(self.user_id,
            self.disabled_token)
        self.assertStatusCode(403, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_user_enabled_invalid_token(self):
        resp, content = common.user_enabled_json(self.user_id,
            self.invalid_token)
        self.assertStatusCode(404, resp, content)

    def test_user_enabled_invalid_token_xml(self):
        resp, content = common.user_enabled_xml(self.user_id,
            self.invalid_token)
        self.assertStatusCode(404, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_user_enabled_missing_token(self):
        resp, content = common.user_enabled_json(self.user_id,
            self.missing_token)
        self.assertStatusCode(401, resp, content)

    def test_user_enabled_missing_token_xml(self):
        resp, content = common.user_enabled_xml(self.user_id,
            self.missing_token)
        self.assertStatusCode(401, resp, content)
        self.assertContentType('application/xml', resp, content)


class TenantUpdateTest(UserTest):

    def setUp(self, *args, **kwargs):
        super(TenantUpdateTest, self).setUp(*args, **kwargs)
        common.create_tenant(self.tenant_id_id, self.admin_token)

    def tearDown(self, *args, **kwargs):
        common.delete_tenant(self.tenant_id_id, self.admin_token)
        super(TenantUpdateTest, self).tearDown(*args, **kwargs)

    def test_update_user_tenant(self):
        resp, content = common.user_tenant_update_json(self.user_id,
            self.tenant_id_id, self.admin_token)
        self.assertStatusCode(200, resp, content)
        self.assertContentType('application/json', resp, content)
        content = json.loads(content)
        self.assertEqual(self.tenant_id_id, content['user']['tenantId'])

    def test_update_user_tenant_xml(self):
        resp, content = common.user_tenant_update_xml(self.user_id,
            self.tenant_id_id, self.admin_token)
        self.assertStatusCode(200, resp, content)
        self.assertContentType('application/xml', resp, content)
        content = etree.fromstring(content)
        self.assertEqual(self.tenant_id_id, content.get("tenantId"))

    def test_update_user_tenant_using_invalid_tenant(self):
        resp, content = common.user_tenant_update_json(self.user_id, "unknown",
            self.admin_token)
        self.assertStatusCode(404, resp, content)

    def test_update_user_tenant_using_disabled_tenant(self):
        resp, content = common.user_tenant_update_json(self.user_id, "disable",
            self.admin_token)
        self.assertStatusCode(404, resp, content)

    def test_update_user_tenant_using_missing_token(self):
        resp, content = common.user_tenant_update_json(self.user_id,
            self.tenant_id2, self.missing_token)
        self.assertStatusCode(401, resp, content)

    def test_update_user_tenant_using_invalid_token(self):
        resp, content = common.user_tenant_update_json(self.user_id,
            self.tenant_id2, self.invalid_token)
        self.assertStatusCode(404, resp, content)

    def test_update_user_tenant_using_disabled_token(self):
        resp, content = common.user_tenant_update_json(
            self.user_id, self.tenant_id2, self.disabled_token)
        self.assertStatusCode(403, resp, content)

    def test_update_user_tenant_using_exp_admin_token(self):
        resp, content = common.user_tenant_update_json(
            self.user_id, self.tenant_id2, self.exp_admin_token)
        self.assertStatusCode(403, resp, content)

    def test_update_user_tenant_xml_using_missing_token(self):
        resp, content = common.user_tenant_update_xml(
            self.user_id, self.tenant_id2, self.missing_token)
        self.assertStatusCode(401, resp, content)

    def test_update_user_tenant_xml_using_invalid_token(self):
        resp, content = common.user_tenant_update_xml(
            self.user_id, self.tenant_id2, self.invalid_token)
        self.assertStatusCode(404, resp, content)

    def test_update_user_tenant_xml_using_disabled_token(self):
        resp, content = common.user_tenant_update_xml(
            self.user_id, self.tenant_id2, self.disabled_token)
        self.assertStatusCode(403, resp, content)

    def test_update_user_tenant_xml_using_exp_admin_token(self):
        resp, content = common.user_tenant_update_xml(
            self.user_id, self.tenant_id2, self.exp_admin_token)
        self.assertStatusCode(403, resp, content)


class AddUserTest(UserTest):

    def test_add_user_tenant(self):
        resp, content = common.create_user_json(self.tenant_id, str(uuid.uuid4()),
            self.admin_token)
        self.assertStatusCode(201, resp, content)

    def test_add_user_tenant_xml(self):
        resp, content = common.create_user_xml(str(self.tenant_id),
            str(uuid.uuid4()), self.admin_token)
        self.assertStatusCode(201, resp, content)

    def test_add_user_tenant_conflict(self):
        resp, content = common.create_user_json(self.tenant_id, self.user_name,
            self.admin_token)
        self.assertStatusCode(409, resp, content)

    def test_add_user_tenant_conflict_xml(self):
        resp, content = common.create_user_xml(self.tenant_id, self.user_name,
            self.admin_token)
        self.assertStatusCode(409, resp, content)

    def test_add_user_tenant_expired_token(self):
        resp, content = common.create_user_json(self.tenant_id, str(uuid.uuid4()),
            self.exp_admin_token)
        self.assertStatusCode(403, resp, content)

    def test_add_user_tenant_expired_token_xml(self):
        resp, content = common.create_user_xml(self.tenant_id, str(uuid.uuid4()),
            self.exp_admin_token)
        self.assertStatusCode(403, resp, content)

    def test_add_user_tenant_disabled_token(self):
        resp, content = common.create_user_json(self.tenant_id, str(uuid.uuid4()),
            self.disabled_token)
        self.assertStatusCode(403, resp, content)

    def test_add_user_tenant_disabled_token_xml(self):
        resp, content = common.create_user_xml(self.tenant_id, str(uuid.uuid4()),
            self.disabled_token)
        self.assertStatusCode(403, resp, content)

    def test_add_user_tenant_invalid_token(self):
        resp, content = common.create_user_json(self.tenant_id, str(uuid.uuid4()),
            self.invalid_token)
        self.assertStatusCode(404, resp, content)

    def test_add_user_tenant_invalid_token_xml(self):
        resp, content = common.create_user_xml(self.tenant_id, self.user_name,
            self.invalid_token)
        self.assertStatusCode(404, resp, content)

    def test_add_user_tenant_missing_token(self):
        resp, content = common.create_user_json(self.tenant_id, str(uuid.uuid4()),
            self.missing_token)
        self.assertStatusCode(401, resp, content)

    def test_add_user_tenant_missing_token_xml(self):
        resp, content = common.create_user_xml(self.tenant_id, str(uuid.uuid4()),
            self.missing_token)
        self.assertStatusCode(401, resp, content)

    def test_add_user_tenant_disabled_tenant(self):
        resp, content = common.create_user_json('0000', str(uuid.uuid4()),
            self.admin_token)
        self.assertStatusCode(403, resp, content)

    def test_add_user_tenant_disabled_tenant_xml(self):
        resp, content = common.create_user_xml('0000', str(uuid.uuid4()),
            self.admin_token)
        self.assertStatusCode(403, resp, content)

if __name__ == '__main__':
    unittest.main()
