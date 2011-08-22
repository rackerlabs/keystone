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


class TenantTest(common.FunctionalTest):
    def setUp(self, *args, **kwargs):
        super(TenantTest, self).setUp(*args, **kwargs)

    def tearDown(self, *args, **kwargs):
        super(TenantTest, self).tearDown(*args, **kwargs)


class CreateTenantTest(TenantTest):

    def test_tenant_create(self):
        common.delete_user(self.user_id, self.admin_token)
        common.delete_tenant(self.tenant, self.admin_token)
        resp, content = common.create_tenant(self.tenant, self.admin_token)
        # this should be either 200 or 201... old code wasn't specific
        self.assertStatusCode(2000, resp, content)

    def test_tenant_create_xml(self):
        common.delete_user(self.user_id, self.admin_token)
        common.delete_tenant_xml(self.tenant, self.admin_token)
        resp, content = common.create_tenant_xml(self.tenant, self.admin_token)
        # this should be either 200 or 201... old code wasn't specific
        self.assertStatusCode(2000, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_tenant_create_again(self):
        resp, content = common.create_tenant(self.tenant, self.admin_token)
        self.assertStatusCode(2000, resp, content)
        self.assertContentType('application/json', resp, content)

        resp, content = common.create_tenant(content['tenant']['id'], self.admin_token)
        self.assertStatusCode(409, resp, content)

    def test_tenant_create_again_xml(self):
        resp, content = common.create_tenant_xml(self.tenant, self.admin_token)
        self.assertStatusCode(2000, resp, content)
        self.assertContentType('application/xml', resp, content)

        resp, content = common.create_tenant_xml(self.tenant, self.admin_token)
        self.assertStatusCode(409, resp, content)
        self.assertContentType('application/xml', resp, content)

    def test_tenant_create_forbidden_token(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant(self.tenant, self.admin_token)
        self.assertStatusCode(200, resp, content)

        url = '%stenants' % (common.URL_V2)
        body = {
            "tenant": {
                "id": content['tenant']['id'],
                "description": "A description ...",
                "enabled": True}}
        resp, content = header.request(url, "POST", body=json.dumps(body),
            headers={
                "Content-Type": "application/json",
                "X-Auth-Token": self.token})
        self.assertStatusCode(409, resp, content)

    def test_tenant_create_forbidden_token_xml(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant_xml(self.tenant, self.admin_token)
        self.assertStatusCode(200, resp, content)
        content = etree.fromstring(content)
        self.tenant = content.get('id')

        url = '%stenants' % (common.URL_V2)
        body = '<?xml version="1.0" encoding="UTF-8"?> \
            <tenant xmlns="http://docs.openstack.org/identity/api/v2.0" \
            enabled="true" id="%s"> \
            <description>A description...</description> \
            </tenant>' % self.tenant
        resp, content = header.request(url, "POST", body=body,
                                  headers={"Content-Type": "application/xml",
                                           "X-Auth-Token": self.token,
                                           "ACCEPT": "application/xml"})
        self.assertStatusCode(401, resp, content)

    def test_tenant_create_expired_token(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant(self.tenant,
                                            self.admin_token)
        if int(resp['status']) == 200:
            self.tenant = content['tenant']['id']
        url = '%stenants' % (common.URL_V2)
        body = {"tenant": {"id": self.tenant,
                           "description": "A description ...",
                           "enabled": True}}
        resp, content = header.request(url, "POST", body=json.dumps(body),
                                headers={"Content-Type": "application/json",
                                         "X-Auth-Token": self.exp_auth_token})
        self.assertStatusCode(403, resp, content)

    def test_tenant_create_expired_token_xml(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant_xml(self.tenant,
                                                self.admin_token)
        content = etree.fromstring(content)
        if int(resp['status']) == 200:
            self.tenant = content.get('id')

        url = '%stenants' % (common.URL_V2)
        body = '<?xml version="1.0" encoding="UTF-8"?> \
            <tenant xmlns="http://docs.openstack.org/identity/api/v2.0" \
            enabled="true" id="%s"> \
            <description>A description...</description> \
            </tenant>' % self.tenant

        resp, content = header.request(url, "POST", body=body,
                                  headers={"Content-Type": "application/xml",
                                           "X-Auth-Token": self.exp_auth_token,
                                           "ACCEPT": "application/xml"})
        self.assertStatusCode(403, resp, content)

    def test_tenant_create_missing_token(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant(self.tenant,
                                            self.admin_token)
        if int(resp['status']) == 200:
            self.tenant = content['tenant']['id']

        url = '%stenants' % (common.URL_V2)
        body = {"tenant": {"id": self.tenant,
                           "description": "A description ...",
                           "enabled": True}}
        resp, content = header.request(url, "POST", body=json.dumps(body),
                                headers={"Content-Type": "application/json"})
        self.assertStatusCode(401, resp, content)

    def test_tenant_create_missing_token_xml(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant_xml(self.tenant,
                                                self.admin_token)
        content = etree.fromstring(content)
        if int(resp['status']) == 200:
            self.tenant = content.get('id')
        url = '%stenants' % (common.URL_V2)
        body = '<?xml version="1.0" encoding="UTF-8"?> \
            <tenant xmlns="http://docs.openstack.org/identity/api/v2.0" \
            enabled="true" id="%s"> \
            <description>A description...</description> \
            </tenant>' % self.tenant
        resp, content = header.request(url, "POST", body=body,
                                  headers={"Content-Type": "application/xml",
                                           "ACCEPT": "application/xml"})
        self.assertStatusCode(401, resp, content)

    def test_tenant_create_disabled_token(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant(self.tenant,
                                            self.admin_token)
        if int(resp['status']) == 200:
            self.tenant = content['tenant']['id']

        url = '%stenants' % (common.URL_V2)
        body = '{"tenant": { "id": "%s", \
                "description": "A description ...", "enabled"\
                :true  } }' % self.tenant
        resp, content = header.request(url, "POST", body=body,
                                  headers={"Content-Type": "application/json",
                                        "X-Auth-Token": self.disabled_token})
        self.assertStatusCode(403, resp, content)

    def test_tenant_create_disabled_token_xml(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant_xml(self.tenant,
                                                self.admin_token)
        content = etree.fromstring(content)
        if int(resp['status']) == 200:
            self.tenant = content.get('id')
        url = '%stenants' % (common.URL_V2)
        body = '<?xml version="1.0" encoding="UTF-8"?> \
            <tenant xmlns="http://docs.openstack.org/identity/api/v2.0" \
            enabled="true" id="%s"> \
            <description>A description...</description> \
            </tenant>' % self.tenant
        resp, content = header.request(url, "POST", body=body,
                                  headers={"Content-Type": "application/xml",
                                           "X-Auth-Token": self.disabled_token,
                                           "ACCEPT": "application/xml"})
        self.assertStatusCode(403, resp, content)

    def test_tenant_create_invalid_token(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant(self.tenant,
                                            self.admin_token)
        if int(resp['status']) == 200:
            self.tenant = content['tenant']['id']

        url = '%stenants' % (common.URL_V2)
        body = '{"tenant": { "id": "%s", \
                "description": "A description ...", "enabled"\
                :true  } }' % self.tenant
        resp, content = header.request(url, "POST", body=body,
                                  headers={"Content-Type": "application/json",
                                           "X-Auth-Token": 'nonexsitingtoken'})
        self.assertStatusCode(404, resp, content)

    def test_tenant_create_invalid_token_xml(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant_xml(self.tenant,
                                                self.admin_token)
        content = etree.fromstring(content)
        if int(resp['status']) == 200:
            self.tenant = content.get('id')

        url = '%stenants' % (common.URL_V2)
        body = '<?xml version="1.0" encoding="UTF-8"?> \
            <tenant xmlns="http://docs.openstack.org/identity/api/v2.0" \
            enabled="true" id="%s"> \
            <description>A description...</description> \
            </tenant>' % self.tenant
        resp, content = header.request(url, "POST", body=body,
                                  headers={"Content-Type": "application/xml",
                                           "X-Auth-Token": 'nonexsitingtoken',
                                           "ACCEPT": "application/xml"})
        self.assertStatusCode(404, resp, content)


class GetTenantsTest(TenantTest):

    def test_get_tenants_using_admin_token(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant(self.tenant, self.admin_token)
        url = '%stenants' % (common.URL_V2)
        self.assertContentType('application/json', resp, content)
        resp, content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/json",
                                         "X-Auth-Token": self.admin_token})
        self.assertStatusCode(200, resp, content)

    def test_get_tenants_using_admin_token_xml(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant(self.tenant, self.admin_token)
        url = '%stenants' % (common.URL_V2)
        self.assertContentType('application/json', resp, content)
        resp, content = header.request(url, "GET", body='',
                                  headers={"Content-Type": "application/xml",
                                           "X-Auth-Token": self.admin_token,
                                           "ACCEPT": "application/xml"})
        self.assertStatusCode(200, resp, content)

    def test_get_tenants_using_user_token(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant(self.tenant, self.admin_token)
        url = '%stenants' % (common.URL_V2)
        self.assertContentType('application/json', resp, content)
        resp, content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/json",
                                           "X-Auth-Token": self.token})
        self.assertStatusCode(200, resp, content)

    def test_get_tenants_using_user_token_xml(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant(self.tenant, self.admin_token)
        url = '%stenants' % (common.URL_V2)
        self.assertContentType('application/json', resp, content)
        resp, content = header.request(url, "GET", body='',
                                  headers={"Content-Type": "application/xml",
                                           "X-Auth-Token": self.token,
                                           "ACCEPT": "application/xml"})
        self.assertStatusCode(200, resp, content)

    def test_get_tenants_exp_token(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant(self.tenant, self.admin_token)
        url = '%stenants' % (common.URL_V2)
        self.assertContentType('application/json', resp, content)
        resp, content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/json",
                                        "X-Auth-Token": self.exp_auth_token})
        self.assertStatusCode(403, resp, content)

    def test_get_tenants_exp_token_xml(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant(self.tenant, self.admin_token)
        url = '%stenants' % (common.URL_V2)
        self.assertContentType('application/json', resp, content)
        resp, content = header.request(url, "GET", body='',
                                  headers={"Content-Type": "application/xml",
                                           "X-Auth-Token": self.exp_auth_token,
                                           "ACCEPT": "application/xml"})
        self.assertStatusCode(403, resp, content)


class GetTenantTest(TenantTest):

    def test_get_tenant(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant(self.tenant, self.admin_token)
        url = '%stenants/%s' % (common.URL_V2, self.tenant)
        self.assertContentType('application/json', resp, content)
        resp, content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/json",
                                           "X-Auth-Token": self.admin_token})
        self.assertStatusCode(200, resp, content)

    def test_get_tenant_xml(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant(self.tenant, self.admin_token)
        url = '%stenants/%s' % (common.URL_V2, self.tenant)
        self.assertContentType('application/json', resp, content)
        resp, content = header.request(url, "GET", body='',
                                  headers={"Content-Type": "application/xml",
                                           "X-Auth-Token": self.admin_token,
                                           "ACCEPT": "application/xml"})
        self.assertStatusCode(200, resp, content)

    def test_get_tenant_bad(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant(self.tenant, self.admin_token)
        url = '%stenants/%s' % (common.URL_V2, 'tenant_bad')
        self.assertContentType('application/json', resp, content)
        resp, content = header.request(url, "GET", body='',
                                  headers={"Content-Type": "application/json",
                                           "X-Auth-Token": self.admin_token})
        self.assertStatusCode(404, resp, content)

    def test_get_tenant_bad_xml(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant(self.tenant, self.admin_token)
        url = '%stenants/%s' % (common.URL_V2, 'tenant_bad')
        self.assertContentType('application/json', resp, content)
        resp, content = header.request(url, "GET", body='',
                                  headers={"Content-Type": "application/xml",
                                           "X-Auth-Token": self.admin_token,
                                           "ACCEPT": "application/xml"})
        self.assertStatusCode(404, resp, content)

    def test_get_tenant_not_found(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant(self.tenant, self.admin_token)
        url = '%stenants/NonexistingID' % (common.URL_V2)
        self.assertContentType('application/json', resp, content)
        resp, content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/json",
                                           "X-Auth-Token": self.admin_token})
        self.assertStatusCode(404, resp, content)

    def test_get_tenant_not_found_xml(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant(self.tenant, self.admin_token)
        url = '%stenants/NonexistingID' % (common.URL_V2)
        self.assertContentType('application/json', resp, content)
        resp, content = header.request(url, "GET", body='',
                                  headers={"Content-Type": "application/xml",
                                           "X-Auth-Token": self.admin_token,
                                           "ACCEPT": "application/xml"})
        self.assertStatusCode(404, resp, content)


class UpdateTenantTest(TenantTest):

    def test_update_tenant(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant(self.tenant, self.admin_token)
        url = '%stenants/%s' % (common.URL_V2, self.tenant)
        data = '{"tenant": { "description": "A NEW description..." ,\
                "enabled":true }}'
        self.assertContentType('application/json', resp, content)
        resp, content = header.request(url, "PUT", body=data,
                                  headers={"Content-Type": "application/json",
                                           "X-Auth-Token": self.admin_token})
        self.assertStatusCode(200, resp, content)
        body = json.loads(content)
        self.assertEqual(self.tenant, body['tenant']['id'])
        self.assertEqual('A NEW description...', body['tenant']['description'])

    def test_update_tenant_xml(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant_xml(self.tenant,
                                                self.admin_token)
        url = '%stenants/%s' % (common.URL_V2, self.tenant)
        data = '<?xml version="1.0" encoding="UTF-8"?> \
             <tenant xmlns="http://docs.openstack.org/identity/api/v2.0" \
             enabled="true"> \
             <description>A NEW description...</description> \
             </tenant>'

        self.assertContentType('application/json', resp, content)
        resp, content = header.request(url, "PUT", body=data,
                                  headers={"Content-Type": "application/xml",
                                           "X-Auth-Token": self.admin_token,
                                           "ACCEPT": "application/xml"})
        self.assertStatusCode(200, resp, content)
        body = etree.fromstring(content)
        desc = body.find(
            "{http://docs.openstack.org/identity/api/v2.0}description")
        self.assertEqual(self.tenant, body.get('id'))
        self.assertEqual('A NEW description...', desc.text)

    def test_update_tenant_bad(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant(self.tenant, self.admin_token)
        url = '%stenants/%s' % (common.URL_V2, self.tenant)
        data = '{"tenant": { "description_bad": "A NEW description...",\
                "enabled":true  }}'
        self.assertContentType('application/json', resp, content)

        resp, content = header.request(url, "PUT", body=data,
                                  headers={"Content-Type": "application/json",
                                           "X-Auth-Token": self.admin_token})
        self.assertStatusCode(400, resp, content)

    def test_update_tenant_bad_xml(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_tenant(self.tenant, self.admin_token)
        url = '%stenants/%s' % (common.URL_V2, self.tenant)
        data = '<?xml version="1.0" encoding="UTF-8"?> \
             <tenant xmlns="http://docs.openstack.org/identity/api/v2.0" \
             enabled="true"> \
             <description_bad>A NEW description...</description> \
             </tenant>'
        self.assertContentType('application/json', resp, content)
        resp, content = header.request(url, "PUT", body=data,
                                  headers={"Content-Type": "application/xml",
                                           "X-Auth-Token": self.admin_token,
                                           "ACCEPT": "application/xml"})
        self.assertStatusCode(400, resp, None)

    def test_update_tenant_not_found(self):
        header = httplib2.Http(".cache")
        url = '%stenants/%s' % (common.URL_V2, common.unique_str())
        data = ('{"tenant": { "description": "A NEW description...", '
            '"enabled":true  }}')
        resp, content = header.request(url, "GET", body=data, headers={
            "Content-Type": "application/json",
            "X-Auth-Token": self.admin_token})
        self.assertContentType('application/json', resp, content)
        self.assertStatusCode(404, resp, content)

    def test_update_tenant_not_found_xml(self):
        header = httplib2.Http(".cache")

        url = '%stenants/%s' % (common.URL_V2, common.unique_str())
        data = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<tenant xmlns="http://docs.openstack.org/identity/api/v2.0" '
            'enabled="true"> '
            '<description_bad>A NEW description...</description> '
            '</tenant>')
        resp, content = header.request(url, "GET", body=data, headers={
            "Content-Type": "application/xml",
            "X-Auth-Token": self.admin_token,
            "ACCEPT": "application/xml"})
        self.assertContentType('application/xml', resp, content)
        self.assertStatusCode(404, resp, content)


class DeleteTenantTest(TenantTest):
    def test_delete_tenant_not_found(self):
        resp = common.delete_tenant(common.unique_str(), self.admin_token)
        self.assertStatusCode(404, resp, None)

    def test_delete_tenant_not_found_xml(self):
        resp = common.delete_tenant_xml(common.unique_str(), self.admin_token)
        self.assertStatusCode(404, resp, None)

    def test_delete_tenant(self):
        tenant_name = common.unique_str()
        tenant_id = self.create_tenant(tenant_name)
        resp = common.delete_tenant(tenant_id, self.admin_token)
        self.assertStatusCode(204, resp, None)

    def test_delete_tenant_xml(self):
        tenant_name = common.unique_str()
        tenant_id = self.create_tenant(tenant_name)
        resp = common.delete_tenant_xml(tenant_id, self.admin_token)
        self.assertStatusCode(204, resp, None)

if __name__ == '__main__':
    unittest.main()
