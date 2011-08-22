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

class ValidateToken(common.FunctionalTest):
    def setUp(self, *args, **kwargs):
        super(ValidateToken, self).setUp(*args, **kwargs)

        # self.user? 'Admin'?
        resp, content = common.create_role_ref(self.user_id, 'Admin',
            self.tenant_id, self.admin_token)
        obj = json.loads(content)

        # This seems very wrong.
        self.role_ref_id = obj['roleRef'].get('id', None)

    def tearDown(self, *args, **kwargs):
        resp, content = common.delete_role_ref(self.user_id, self.role_ref_id,
            self.admin_token)

        super(ValidateToken, self).tearDown(*args, **kwargs)

    def test_validate_token_true(self):
        header = httplib2.Http(".cache")

        url = '%stokens/%s?belongsTo=%s' % (common.URL_V2, self.token,
            self.tenant)
        resp, content = header.request(url, "GET", body='', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": self.admin_token})
        if int(resp['status']) == 500:
            self.fail('Identity Fault')
        elif int(resp['status']) == 503:
            self.fail('Service Not Available')
        self.assertEqual(200, int(resp['status']))
        self.assertEqual('application/json', common.content_type(resp))
        #verify content
        obj = json.loads(content)
        if not "auth" in obj:
            raise self.fail("Expecting Auth")
        role_refs = obj["auth"]["user"]["roleRefs"]
        role_ref = role_refs[0]
        role_ref_id = role_ref["id"]
        self.assertEqual(self.role_ref_id, role_ref_id)

    def test_validate_token_true_using_service_token(self):
        header = httplib2.Http(".cache")

        url = '%stokens/%s?belongsTo=%s' % (common.URL_V2, self.token,
            self.tenant)
        resp, content = header.request(url, "GET", body='', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": self.service_token})
        if int(resp['status']) == 500:
            self.fail('Identity Fault')
        elif int(resp['status']) == 503:
            self.fail('Service Not Available')
        self.assertEqual(200, int(resp['status']))
        self.assertEqual('application/json', common.content_type(resp))
        #verify content
        obj = json.loads(content)
        if not "auth" in obj:
            raise self.fail("Expecting Auth")
        role_refs = obj["auth"]["user"]["roleRefs"]
        role_ref = role_refs[0]
        role_ref_id = role_ref["id"]
        self.assertEqual(self.role_ref_id, role_ref_id)

    def test_validate_token_true_xml(self):
        header = httplib2.Http(".cache")
        url = '%stokens/%s?belongsTo=%s' % (
            common.URL_V2, self.token, self.tenant)
        resp, content = header.request(url, "GET", body='', headers={
            "Content-Type": "application/xml",
            "X-Auth-Token": self.admin_token,
            "ACCEPT": "application/xml"})
        if int(resp['status']) == 500:
            self.fail('Identity Fault')
        elif int(resp['status']) == 503:
            self.fail('Service Not Available')
        self.assertEqual(200, int(resp['status']))
        self.assertEqual('application/xml', common.content_type(resp))
        #verify content
        dom = etree.Element("root")
        dom.append(etree.fromstring(content))
        auth = dom.find("{http://docs.openstack.org/identity/api/v2.0}" \
            "auth")
        if auth == None:
            self.fail("Expecting Auth")

        user = auth.find("{http://docs.openstack.org/identity/api/v2.0}" \
            "user")
        if user == None:
            self.fail("Expecting User")
        roleRefs = user.find("{http://docs.openstack.org/identity/api/v2.0}" \
               "roleRefs")
        if roleRefs == None:
            self.fail("Expecting Role Refs")
        roleRef = roleRefs.find(
            "{http://docs.openstack.org/identity/api/v2.0}roleRef")
        if roleRef == None:
            self.fail("Expecting Role Refs")
        self.assertEqual(str(self.role_ref_id), roleRef.get("id"))

    def test_validate_token_expired(self):
        header = httplib2.Http(".cache")
        url = '%stokens/%s?belongsTo=%s' % (common.URL_V2, self.exp_auth_token,
                                           self.tenant)
        resp, _content = header.request(url, "GET", body='',
                                  headers={"Content-Type": "application/json",
                                         "X-Auth-Token": self.exp_auth_token})
        if int(resp['status']) == 500:
            self.fail('Identity Fault')
        elif int(resp['status']) == 503:
            self.fail('Service Not Available')
        self.assertEqual(403, int(resp['status']))
        self.assertEqual('application/json', common.content_type(resp))

    def test_validate_token_expired_xml(self):
        header = httplib2.Http(".cache")

        url = '%stokens/%s?belongsTo=%s' % (common.URL_V2, self.exp_auth_token,
                                           self.tenant)
        resp, _content = header.request(url, "GET", body='',
                                  headers={"Content-Type": "application/xml",
                                           "X-Auth-Token": self.exp_auth_token,
                                           "ACCEPT": "application/xml"})
        if int(resp['status']) == 500:
            self.fail('Identity Fault')
        elif int(resp['status']) == 503:
            self.fail('Service Not Available')
        self.assertEqual(403, int(resp['status']))
        self.assertEqual('application/xml', common.content_type(resp))

    def test_validate_token_invalid(self):
        header = httplib2.Http(".cache")
        url = '%stokens/%s?belongsTo=%s' % (common.URL_V2, 'NonExistingToken',
                                           self.tenant)
        resp, _content = header.request(url, "GET", body='',
                                  headers={"Content-Type": "application/json",
                                           "X-Auth-Token": self.admin_token})

        if int(resp['status']) == 500:
            self.fail('Identity Fault')
        elif int(resp['status']) == 503:
            self.fail('Service Not Available')
        self.assertEqual(401, int(resp['status']))
        self.assertEqual('application/json', common.content_type(resp))

    def test_validate_token_invalid_xml(self):
        header = httplib2.Http(".cache")
        url = '%stokens/%s?belongsTo=%s' % (common.URL_V2, 'NonExistingToken',
                                           self.tenant)
        resp, _content = header.request(url, "GET", body='',
                                  headers={"Content-Type": "application/json",
                                           "X-Auth-Token": self.admin_token})
        if int(resp['status']) == 500:
            self.fail('Identity Fault')
        elif int(resp['status']) == 503:
            self.fail('Service Not Available')
        self.assertEqual(401, int(resp['status']))
        self.assertEqual('application/json', common.content_type(resp))

if __name__ == '__main__':
    unittest.main()
