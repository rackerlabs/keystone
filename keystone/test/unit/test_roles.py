# vim: tabstop=4 shiftwidth=4 softtabstop=4
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

from keystone.test.unit import common


class RolesTest(common.FunctionalTest):
    def setUp(self, *args, **kwargs):
        super(RolesTest, self).setUp(*args, **kwargs)

    def tearDown(self, *args, **kwargs):
        super(RolesTest, self).tearDown(*args, **kwargs)


class CreateRolesTest(RolesTest):
    def test_create_role(self):
        resp, content = common.create_role('test_role', self.admin_token)
        self.assertStatusCode(201, resp, content)
        resp, content = common.delete_role('test_role', self.admin_token)
        self.assertStatusCode(204, resp, content)

    def test_create_role_using_service_token(self):
        resp, content = common.create_role('test_role', self.service_token)
        self.assertStatusCode(201, resp, content)
        resp, content = common.delete_role('test_role', self.service_token)
        self.assertStatusCode(204, resp, content)

    def test_create_roles_using_invalid_tokens(self):
        resp, content = common.create_role('test_role', self.disabled_token)
        self.assertStatusCode(403, resp, content)
        resp, content = common.create_role('test_role', self.missing_token)
        self.assertStatusCode(401, resp, content)
        resp, content = common.create_role('test_role', self.exp_auth_token)
        self.assertStatusCode(403, resp, content)
        resp, content = common.create_role('test_role', self.invalid_token)
        self.assertStatusCode(404, resp, content)

    def test_delete_roles_using_invalid_tokens(self):
        resp, content = common.delete_role('test_role', self.disabled_token)
        self.assertStatusCode(403, resp, content)
        resp, content = common.delete_role('test_role', self.missing_token)
        self.assertStatusCode(401, resp, content)
        resp, content = common.delete_role('test_role', self.exp_auth_token)
        self.assertStatusCode(403, resp, content)
        resp, content = common.delete_role('test_role', self.invalid_token)
        self.assertStatusCode(404, resp, content)

    def test_create_and_delete_role_that_has_references(self):
        resp, content = common.create_role('test_role', self.admin_token)
        self.assertStatusCode(201, resp, content)
        common.create_role_ref(
            self.user, "test_role",
            self.tenant, self.admin_token)
        resp, content = common.delete_role('test_role', self.admin_token)
        self.assertStatusCode(204, resp, content)

    def test_create_role_mapped_to_a_service(self):
        resp, content = common.create_role_mapped_to_service(
            self.service_role, self.admin_token, self.service_id)
        self.assertStatusCode(201, resp, content)
        resp, content = common.get_role(self.service_role, self.admin_token)
        self.assertStatusCode(200, resp, content)

        obj = json.loads(content)
        self.assertEqual(obj['role']['id'], self.service_role, (resp, content))
        self.assertEqual(obj['role']['serviceId'], self.service_id, (resp, content))

        resp, content = common.delete_role(self.service_role, self.admin_token)
        self.assertStatusCode(204, resp, content)

    def test_create_role_mapped_to_a_service_xml(self):
        resp, content = common.create_role_mapped_to_service_xml(
            self.service_role, self.admin_token, self.service_id)
        self.assertStatusCode(201, resp, content)
        resp, content = common.get_role_xml(self.service_role, self.admin_token)
        self.assertStatusCode(200, resp, content)

        #verify content
        dom = etree.Element("root")
        dom.append(etree.fromstring(content))
        role = dom.find("{http://docs.openstack.org/identity/api/v2.0}" \
            "role")
        self.assertIs
        if role == None:
            self.fail("Expecting Role")
        role_id = role.get("id")
        if role_id != self.service_role:
            self.fail("Not the expected Role")
        service_id = role.get("serviceId")

        if service_id != self.service_id:
            self.fail("Not the expected service")
        resp, content = common.delete_role(self.service_role, self.admin_token)
        self.assertStatusCode(204, resp, content)

    def test_create_role_mapped_to_a_service_using_incorrect_role_name(self):
        resp, content = common.create_role_mapped_to_service(
            'test_role', self.admin_token, self.service_id)
        self.assertStatusCode(400, resp, content)


class GetRolesTest(RolesTest):
    def test_get_roles(self):
        header = httplib2.Http(".cache")
        url = '%sroles' % (common.URL_V2)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/json",
                                         "X-Auth-Token": self.admin_token})
        self.assertStatusCode(200, resp, content)

        #verify content
        obj = json.loads(content)
        if not "roles" in obj:
            raise self.fail("Expecting Roles")
        roles = obj["roles"]["values"]
        if len(roles) != 3:
            self.fail("Roles not of required length.")

        role = roles[0]
        if not "id" in role:
            role_id = None
        else:
            role_id = role["id"]
        if role_id not in ['Admin', 'Member', 'KeystoneServiceAdmin']:
            self.fail("Not the expected Role")

    def test_get_roles_using_service_admin_token(self):
        header = httplib2.Http(".cache")
        url = '%sroles' % (common.URL_V2)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/json",
                                         "X-Auth-Token": self.service_token})
        self.assertStatusCode(200, resp, content)

        #verify content
        obj = json.loads(content)
        if not "roles" in obj:
            raise self.fail("Expecting Roles")
        roles = obj["roles"]["values"]
        if len(roles) != 3:
            self.fail("Roles not of required length.")

        role = roles[0]
        if not "id" in role:
            role_id = None
        else:
            role_id = role["id"]
        if role_id not in ['Admin', 'Member', 'KeystoneServiceAdmin']:
            self.fail("Not the expected Role")

    def test_get_roles_xml(self):
        header = httplib2.Http(".cache")
        url = '%sroles' % (common.URL_V2)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='',
                                  headers={"Content-Type": "application/xml",
                                           "X-Auth-Token": self.admin_token,
                                           "ACCEPT": "application/xml"})
        self.assertStatusCode(200, resp, content)
        # Validate Returned Content
        dom = etree.Element("root")
        dom.append(etree.fromstring(content))
        roles = dom.find("{http://docs.openstack.org/identity/api/v2.0}" \
            "roles")
        if roles == None:
            self.fail("Expecting Roles")
        roles = roles.findall("{http://docs.openstack.org/identity/api/v2.0}" \
            "role")
        if len(roles) != 3:
            self.fail("Not the expected Role count")
        for role in roles:
            if role.get("id") not in ['Admin', 'Member', \
                 'KeystoneServiceAdmin']:
                self.fail("Unexpected Role")

    def test_get_roles_exp_token(self):
        header = httplib2.Http(".cache")
        url = '%sroles' % (common.URL_V2)
        resp, content = header.request(url, "GET", body='{}', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": self.exp_auth_token})
        self.assertContentType('application/json', resp, content)
        self.assertStatusCode(403, resp, content)

    def test_get_roles_exp_token_xml(self):
        header = httplib2.Http(".cache")
        url = '%sroles' % (common.URL_V2)
        resp, content = header.request(url, "GET", body='', headers={
            "Content-Type": "application/xml",
            "X-Auth-Token": self.exp_auth_token,
            "ACCEPT": "application/xml"})
        self.assertContentType('application/xml', resp, content)
        self.assertStatusCode(403, resp, content)


class GetRoleTest(RolesTest):
    role = None

    def test_get_role(self):
        self.role = 'Admin'
        header = httplib2.Http(".cache")
        url = '%sroles/%s' % (common.URL_V2, self.role)
        resp, content = header.request(url, "GET", body='{}', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": self.admin_token})
        self.assertContentType('application/json', resp, content)
        self.assertStatusCode(200, resp, content)

        obj = json.loads(content)
        self.assertEqual(obj['role']['id'], 'Admin', (resp, content))

    def test_get_role_using_service_admin_token(self):
        self.role = 'Admin'
        header = httplib2.Http(".cache")
        url = '%sroles/%s' % (common.URL_V2, self.role)
        resp, content = header.request(url, "GET", body='{}', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": self.service_token})
        self.assertContentType('application/json', resp, content)
        self.assertStatusCode(200, resp, content)

        obj = json.loads(content)
        self.assertEqual(obj['role']['id'], 'Admin', (resp, content))

    def test_get_role_xml(self):
        self.role = 'Admin'
        header = httplib2.Http(".cache")
        url = '%sroles/%s' % (common.URL_V2, self.role)
        resp, content = header.request(url, "GET", body='',
                                  headers={"Content-Type": "application/xml",
                                           "X-Auth-Token": self.admin_token,
                                           "ACCEPT": "application/xml"})
        self.assertContentType('application/xml', resp, content)
        self.assertEqual(200, int(resp['status']))

        #verify content
        dom = etree.Element("root")
        dom.append(etree.fromstring(content))
        role = dom.find("{http://docs.openstack.org/identity/api/v2.0}" \
            "role")
        if role == None:
            self.fail("Expecting Role")
        role_id = role.get("id")
        if role_id != 'Admin':
            self.fail("Not the expected Role")

    def test_get_role_bad(self):
        header = httplib2.Http(".cache")
        url = '%sroles/%s' % (common.URL_V2, 'tenant_bad')
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='',
                                  headers={"Content-Type": "application/json",
                                           "X-Auth-Token": self.admin_token})
        self.assertEqual(404, int(resp['status']))

    def test_get_role_xml_bad(self):
        header = httplib2.Http(".cache")
        url = '%sroles/%s' % (common.URL_V2, 'tenant_bad')
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='',
                                  headers={"Content-Type": "application/json",
                                           "X-Auth-Token": self.admin_token})
        self.assertEqual(404, int(resp['status']))

    def test_get_role_expired_token(self):
        self.role = 'Admin'
        header = httplib2.Http(".cache")
        url = '%sroles/%s' % (common.URL_V2, self.role)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}',
            headers={"Content-Type": "application/json",
                "X-Auth-Token": self.exp_auth_token})
        self.assertEqual(403, int(resp['status']))

    def test_get_role_xml_using_expired_token(self):
        self.role = 'Admin'
        header = httplib2.Http(".cache")
        url = '%sroles/%s' % (common.URL_V2, self.role)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='',
                                  headers={"Content-Type": "application/xml",
                                           "X-Auth-Token": self.exp_auth_token,
                                           "ACCEPT": "application/xml"})
        self.assertEqual(403, int(resp['status']))

    def test_get_role_using_disabled_token(self):
        self.role = 'Admin'
        header = httplib2.Http(".cache")
        url = '%sroles/%s' % (common.URL_V2, self.role)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}',
            headers={"Content-Type": "application/json",
                "X-Auth-Token": self.disabled_token})
        if int(resp['status']) == 500:
            self.fail('Identity Fault')
        elif int(resp['status']) == 503:
            self.fail('Service Not Available')
        self.assertEqual(403, int(resp['status']))

    def test_get_role_xml_using_disabled_token(self):
        self.role = 'Admin'
        header = httplib2.Http(".cache")
        url = '%sroles/%s' % (common.URL_V2, self.role)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='',
                                  headers={"Content-Type": "application/xml",
                                           "X-Auth-Token": self.disabled_token,
                                           "ACCEPT": "application/xml"})
        self.assertEqual(403, int(resp['status']))

    def test_get_role_using_missing_token(self):
        self.role = 'Admin'
        header = httplib2.Http(".cache")
        url = '%sroles/%s' % (common.URL_V2, self.role)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/json",
                                           "X-Auth-Token": self.missing_token})
        self.assertEqual(401, int(resp['status']))

    def test_get_role_xml_using_missing_token(self):
        self.role = 'Admin'
        header = httplib2.Http(".cache")
        url = '%sroles/%s' % (common.URL_V2, self.role)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='',
                                  headers={"Content-Type": "application/xml",
                                           "X-Auth-Token": self.missing_token,
                                           "ACCEPT": "application/xml"})
        self.assertEqual(401, int(resp['status']))

    def test_get_role_using_invalid_token(self):
        self.role = 'Admin'
        header = httplib2.Http(".cache")
        url = '%sroles/%s' % (common.URL_V2, self.role)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/json",
                                           "X-Auth-Token": self.invalid_token})
        self.assertEqual(404, int(resp['status']))

    def test_get_role_xml_using_invalid_token(self):
        self.role = 'Admin'
        header = httplib2.Http(".cache")
        url = '%sroles/%s' % (common.URL_V2, self.role)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='',
                                  headers={"Content-Type": "application/xml",
                                           "X-Auth-Token": self.invalid_token,
                                           "ACCEPT": "application/xml"})
        self.assertEqual(404, int(resp['status']))


class CreateRoleRefTest(RolesTest):
    def test_role_ref_create_json(self):
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(self.user, 'Admin', self.tenant,
            self.admin_token)
        resp_val = int(resp['status'])
        self.assertEqual(201, resp_val)

    def test_role_ref_create_xml(self):
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref_xml(
            self.user, 'Admin', self.tenant,
                self.admin_token)
        resp_val = int(resp['status'])
        self.assertEqual(201, resp_val)

    def test_role_ref_create_json_using_service_admin_token(self):
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(self.user, 'Admin', self.tenant,
            self.service_token)
        resp_val = int(resp['status'])
        self.assertEqual(201, resp_val)

    def test_role_ref_create_json_using_expired_token(self):
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(self.user, 'Admin', self.tenant,
            str(self.exp_auth_token))
        resp_val = int(resp['status'])
        self.assertEqual(403, resp_val)

    def test_role_ref_create_json_using_disabled_token(self):
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(self.user, 'Admin', self.tenant,
            str(self.disabled_token))
        resp_val = int(resp['status'])
        self.assertEqual(403, resp_val)

    def test_role_ref_create_json_using_missing_token(self):
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(self.user, 'Admin', self.tenant,
            str(self.missing_token))
        resp_val = int(resp['status'])
        self.assertEqual(401, resp_val)

    def test_role_ref_create_json_using_invalid_token(self):
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(self.user, 'Admin', self.tenant,
            str(self.invalid_token))
        resp_val = int(resp['status'])
        self.assertEqual(404, resp_val)


class GetRoleRefsTest(RolesTest):
    def test_get_rolerefs(self):
        header = httplib2.Http(".cache")
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(
            self.user, 'Admin', self.tenant,
                self.admin_token)
        url = '%susers/%s/roleRefs' % (common.URL_V2, self.user)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/json",
                                         "X-Auth-Token": self.admin_token})
        self.assertEqual(200, int(resp['status']))

        #verify content
        obj = json.loads(content)
        if not "roleRefs" in obj:
            raise self.fail("Expecting RoleRefs")

    def test_get_rolerefs_xml(self):
        header = httplib2.Http(".cache")
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(
            self.user, 'Admin', self.tenant,
                self.admin_token)
        url = '%susers/%s/roleRefs' % (common.URL_V2, self.user)
        #test for Content-Type = application/xml
        resp, content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/xml",
                                         "X-Auth-Token": self.admin_token,
                                         "ACCEPT": "application/xml"})
        self.assertEqual(200, int(resp['status']))
        #verify content
        dom = etree.Element("root")
        dom.append(etree.fromstring(content))
        roles = dom.find("{http://docs.openstack.org/identity/api/v2.0}" \
            "roleRefs")
        if roles == None:
            self.fail("Expecting Role Refs")

    def test_get_rolerefs_xml_using_service_admin_token(self):
        header = httplib2.Http(".cache")
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(
            self.user, 'Admin', self.tenant,
                self.admin_token)
        url = '%susers/%s/roleRefs' % (common.URL_V2, self.user)
        #test for Content-Type = application/xml
        resp, content = header.request(url, "GET", body='{}',
            headers={"Content-Type": "application/xml",
            "X-Auth-Token": self.service_token,
            "ACCEPT": "application/xml"})
        self.assertEqual(200, int(resp['status']))
        #verify content
        dom = etree.Element("root")
        dom.append(etree.fromstring(content))
        roles = dom.find("{http://docs.openstack.org/identity/api/v2.0}" \
            "roleRefs")
        if roles == None:
            self.fail("Expecting Role Refs")

    def test_get_rolerefs_using_expired_token(self):
        header = httplib2.Http(".cache")
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(self.user,
            'Admin', self.tenant,
                self.admin_token)
        url = '%susers/%s/roleRefs' % (common.URL_V2, self.user)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}',
            headers={"Content-Type": "application/json",
                "X-Auth-Token": str(self.exp_auth_token)})
        self.assertStatusCode(403, resp, content)

    def test_get_rolerefs_xml_using_expired_token(self):
        header = httplib2.Http(".cache")
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(
            self.user, 'Admin', self.tenant,
                self.admin_token)
        url = '%susers/%s/roleRefs' % (common.URL_V2, self.user)
        #test for Content-Type = application/xml
        resp, content = header.request(url, "GET", body='{}',
            headers={"Content-Type": "application/xml",
                "X-Auth-Token": str(self.exp_auth_token),
                    "ACCEPT": "application/xml"})
        self.assertStatusCode(403, resp, content)

    def test_get_rolerefs_using_disabled_token(self):
        header = httplib2.Http(".cache")
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(self.user,
            'Admin', self.tenant, self.admin_token)
        url = '%susers/%s/roleRefs' % (common.URL_V2, self.user)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}',
            headers={"Content-Type": "application/json",
                "X-Auth-Token": str(self.disabled_token)})
        self.assertStatusCode(403, resp, content)

    def test_get_rolerefs_xml_using_disabled_token(self):
        header = httplib2.Http(".cache")
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(
            self.user, 'Admin', self.tenant,
                self.admin_token)
        url = '%susers/%s/roleRefs' % (common.URL_V2, self.user)
        #test for Content-Type = application/xml
        resp, content = header.request(url, "GET", body='{}',
            headers={"Content-Type": "application/xml",
                "X-Auth-Token": str(self.disabled_token),
                    "ACCEPT": "application/xml"})
        self.assertStatusCode(403, resp, content)

    def test_get_rolerefs_using_missing_token(self):
        header = httplib2.Http(".cache")
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(self.user, 'Admin',
            self.tenant, self.admin_token)
        url = '%susers/%s/roleRefs' % (common.URL_V2, self.user)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": str(self.missing_token)})
        self.assertStatusCode(401, resp, content)

    def test_get_rolerefs_xml_using_missing_token(self):
        header = httplib2.Http(".cache")
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(self.user, 'Admin',
            self.tenant, self.admin_token)
        url = '%susers/%s/roleRefs' % (common.URL_V2, self.user)
        #test for Content-Type = application/xml
        resp, content = header.request(url, "GET", body='{}', headers={
            "Content-Type": "application/xml",
            "X-Auth-Token": str(self.missing_token),
            "ACCEPT": "application/xml"})
        self.assertStatusCode(401, resp, content)

    def test_get_rolerefs_json_using_invalid_token(self):
        header = httplib2.Http(".cache")
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(self.user, 'Admin',
            self.tenant, self.admin_token)
        url = '%susers/%s/roleRefs' % (common.URL_V2, self.user)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": str(self.invalid_token)})
        self.assertStatusCode(404, resp, content)

    def test_get_rolerefs_xml_using_invalid_token(self):
        header = httplib2.Http(".cache")
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(self.user, 'Admin', self.tenant, self.admin_token)
        url = '%susers/%s/roleRefs' % (common.URL_V2, self.user)
        resp, content = header.request(url, "GET", body='{}', headers={
            "Content-Type": "application/xml",
            "X-Auth-Token": str(self.invalid_token),
            "ACCEPT": "application/xml"})
        self.assertStatusCode(404, resp, content)
        self.assertContentType('application/xml', resp, content)


class DeleteRoleRefTest(RolesTest):
    def test_delete_roleref(self):
        header = httplib2.Http(".cache")
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(self.user, 'Admin', self.tenant,
            self.admin_token)
        self.assertStatusCode(201, resp, content)
        obj = json.loads(content)
        self.assertIsNotNone(obj['roleRef']['id'], (resp, content))

        url = '%susers/%s/roleRefs/%s' % (common.URL_V2, self.user, obj['roleRef']['id'])
        resp, content = header.request(url, "DELETE", body='', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": self.admin_token})
        self.assertStatusCode(204, resp, content)

    def test_delete_roleref_using_service_admin_token(self):
        header = httplib2.Http(".cache")
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(self.user, 'Admin', self.tenant,
            self.admin_token)
        self.assertStatusCode(201, resp, content)

        obj = json.loads(content)
        self.assertIsNotNone(obj['roleRef']['id'], (resp, content))

        url = '%susers/%s/roleRefs/%s' % (common.URL_V2, self.user, obj['roleRef']['id'])
        resp, content = header.request(url, "DELETE", body='', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": self.service_token})
        self.assertStatusCode(204, resp, content)

    def test_delete_roleref_using_expired_token(self):
        header = httplib2.Http(".cache")
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(self.user, 'Admin', self.tenant,
            self.admin_token)
        self.assertStatusCode(201, resp, content)
        obj = json.loads(content)
        self.assertIsNotNone(obj['roleRef']['id'], (resp, content))
        url = '%susers/%s/roleRefs/%s' % (common.URL_V2, self.user, obj['roleRef']['id'])
        resp, content = header.request(url, "DELETE", body='', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": str(self.exp_auth_token)})
        self.assertStatusCode(403, resp, content)

    def test_delete_roleref_using_disabled_token(self):
        header = httplib2.Http(".cache")
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(self.user, 'Admin', self.tenant,
            self.admin_token)
        self.assertStatusCode(201, resp, content)

        obj = json.loads(content)
        self.assertIsNotNone(obj['roleRef']['id'], (resp, content))

        url = '%susers/%s/roleRefs/%s' % (common.URL_V2, self.user, obj['roleRef']['id'])
        resp, content = header.request(url, "DELETE", body='', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": str(self.disabled_token)})
        self.assertStatusCode(403, resp, content)

    def test_delete_roleref_using_missing_token(self):
        header = httplib2.Http(".cache")
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(self.user, 'Admin', self.tenant,
            self.admin_token)
        self.assertStatusCode(201, resp, content)

        obj = json.loads(content)
        self.assertIsNotNone(obj['roleRef']['id'], (resp, content))

        url = '%susers/%s/roleRefs/%s' % (common.URL_V2, self.user, obj['roleRef']['id'])
        resp, content = header.request(url, "DELETE", body='',
            headers={"Content-Type": "application/json",
                "X-Auth-Token": str(self.missing_token)})
        self.assertStatusCode(401, resp, content)

    def test_delete_roleref_using_invalid_token(self):
        header = httplib2.Http(".cache")
        common.add_user_json(self.admin_token)
        resp, content = common.create_role_ref(self.user, 'Admin', self.tenant,
            self.admin_token)
        self.assertStatusCode(201, resp, content)

        obj = json.loads(content)
        self.assertIsNotNone(obj['roleRef']['id'], (resp, content))

        url = '%susers/%s/roleRefs/%s' % (common.URL_V2, self.user, obj['roleRef']['id'])
        resp, content = header.request(url, "DELETE", body='',
              headers={"Content-Type": "application/json",
                       "X-Auth-Token": str(self.invalid_token)})
        self.assertStatusCode(404, resp, content)


if __name__ == '__main__':
    unittest.main()
