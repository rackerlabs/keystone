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


import httplib2
import json
from lxml import etree
import unittest2 as unittest

from keystone.test.unit import common


class AuthenticationTest(common.FunctionalTest):
    def setUp(self, *args, **kwargs):
        super(AuthenticationTest, self).setUp(*args, **kwargs)

        common.delete_all_endpoint(self.tenant_id, self.admin_token)
        common.create_endpoint(self.tenant_id, "1", self.admin_token)
        common.create_endpoint(self.tenant_id, "2", self.admin_token)
        common.create_endpoint(self.tenant_id, "3", self.admin_token)
        common.create_endpoint(self.tenant_id, "4", self.admin_token)

    def tearDown(self):
        common.delete_all_endpoint(self.tenant_id, self.admin_token)

    def test_authorize(self):
        resp, content = common.get_token('joeuser', 'secrete', self.tenant_id)
        self.assertStatusCode(200, resp, content)
        self.assertContentType('application/json', resp, content)
        self.assertTrue("auth" in content, (resp, content))
        self.assertTrue("serviceCatalog" in content, (resp, content))

    def test_authorize_xml(self):
        resp, content = common.get_token_xml('joeuser', 'secrete',
            self.tenant_id)
        self.assertStatusCode(200, resp, content)
        self.assertContentType('application/xml', resp, content)

        dom = etree.Element("root")
        dom.append(etree.fromstring(content))

        auth = dom.find("{http://docs.openstack.org/identity/api/v2.0}"
            "auth")
        self.assertIsNotNone(auth, (resp, content))

        service_catalog = auth.find(
            "{http://docs.openstack.org/identity/api/v2.0}"
                "serviceCatalog")
        self.assertIsNotNone(service_catalog, (resp, content))

    def test_authorize_legacy(self):
        resp, content = common.get_token_legacy('joeuser', 'secrete')
        self.assertStatusCode(204, resp, content)
        self.assertTrue(resp['x-auth-token'])
        self.assertTrue(resp['x-server-management-url'])
        self.assertTrue(resp['x-storage-url'])
        self.assertTrue(resp['x-glance'])
        self.assertTrue(resp['x-identity'])

    def test_authorize_user_disabled(self):
        header = httplib2.Http(".cache")
        url = '%stokens' % common.URL_V2
        body = {
            "passwordCredentials": {
                "username": self.disabled_user_id,
                "password": "secrete",
                "tenantId": self.tenant_id}}
        resp, content = header.request(url, "POST", body=json.dumps(body),
            headers={
                "Content-Type": "application/json"})
        self.assertStatusCode(403, resp, content)
        self.assertContentType('application/json', resp, content)

    def test_authorize_user_disabled_xml(self):
        header = httplib2.Http(".cache")
        url = '%stokens' % common.URL_V2
        body = '<?xml version="1.0" encoding="UTF-8"?> \
                <passwordCredentials \
                xmlns="http://docs.openstack.org/identity/api/v2.0" \
                password="secrete" username="%s" \
                tenantId="%s"/>' % (self.disabled_user_id, self.tenant_id)
        resp, content = header.request(url, "POST", body=body, headers={
            "Content-Type": "application/xml",
            "ACCEPT": "application/xml"})
        self.assertStatusCode(403, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_authorize_user_wrong(self):
        header = httplib2.Http(".cache")
        url = '%stokens' % common.URL_V2
        body = {
            "passwordCredentials": {
                "username-w": "disabled",
                "password": "secrete",
                "tenantId": self.tenant_id}}
        resp, content = header.request(url, "POST", body=json.dumps(body),
            headers={
                "Content-Type": "application/json"})
        content = json.loads(content)
        self.assertStatusCode(400, resp, content)
        self.assertContentType('application/json', resp, content)

    def test_authorize_user_wrong_xml(self):
        header = httplib2.Http(".cache")
        url = '%stokens' % common.URL_V2
        body = '<?xml version="1.0" encoding="UTF-8"?> \
                <passwordCredentials \
                xmlns="http://docs.openstack.org/identity/api/v2.0" \
                password="secrete" username-w="disabled" \
                tenantId="%s"/>' % self.tenant_id
        resp, content = header.request(url, "POST", body=body,
            headers={
                "Content-Type": "application/xml",
                "ACCEPT": "application/xml"})
        self.assertStatusCode(400, resp, content)
        self.assertContentType('application/xml', resp, content)


class MultiToken(common.FunctionalTest):
    def setUp(self, *args, **kwargs):
        super(MultiToken, self).setUp(*args, **kwargs)

        self.tenant_name2 = common.unique_str()
        self.tenant_id2 = common.create_tenant(self.tenant_name2, self.admin_token)

        self.user_name2 = common.unique_str()
        self.user_password2 = common.unique_str()
        self.user_email2 = common.unique_str() + '@openstack.org'
        self.user_id2 = self.create_user(self.user_name2, self.user_password2, self.user_email2, self.tenant_id2)

        common.add_user_json(self.admin_token)

    def tearDown(self, *args, **kwargs):
        self.delete_user(self.user_id2)
        self.delete_tenant(self.tenant_id2)

        super(MultiToken, self).tearDown(*args, **kwargs)

    def test_unassigned_user(self):
        resp, content = common.get_token(self.user_name2, self.user_password2, self.tenant_id1)
        self.assertStatusCode(401, resp, content)


if __name__ == '__main__':
    unittest.main()
