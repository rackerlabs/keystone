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

class EndpointTemplatesTest(common.FunctionalTest):
    def setUp(self, *args, **kwargs):
        super(EndpointTemplatesTest, self).setUp(*args, **kwargs)

        self.region = 'DFW'
        self.service = common.get_test_service_id()
        self.public_url = 'public'
        self.admin_url = 'admin'
        self.internal_url = 'internal'
        self.enabled = True
        self.is_global = False
        resp, content = common.create_endpoint_template(self.region,
            self.service, self.public_url, self.admin_url, self.internal_url,
            self.enabled, self.is_global, self.admin_token)
        self.assertStatusCode(201, resp, content)
        obj = json.loads(content)
        self.endpoint_template_id = obj["endpointTemplate"].get('id')

    def tearDown(self, *args, **kwargs):
        common.delete_endpoint_template(self.endpoint_template_id,
            self.admin_token)
        common.delete_all_endpoint(self.tenant_id, self.admin_token)

        super(EndpointTemplatesTest, self).tearDown(*args, **kwargs)


class CreateEndpointTemplatesTest(EndpointTemplatesTest):
    def test_create_endpoint_template(self):
        resp, content = common.create_endpoint_template(
            self.region, self.service, self.public_url,
            self.admin_url, self.internal_url,
            self.enabled, self.is_global, self.admin_token)
        self.assertStatusCode(201, resp, content)

        obj = json.loads(content)
        self.assertIsNotNone(obj['endpointTemplate']['id'], (resp, content))
        self.assertIsNotNone(obj['endpointTemplate']['serviceId'], (resp, content))

        resp, content = common.delete_endpoint_template(
            obj['endpointTemplate']['id'], self.admin_token)
        self.assertStatusCode(204, resp, content)

    def test_create_and_delete_endpoint_template_that_has_dependencies(self):
        resp, content = common.create_endpoint_template(self.region,
            self.service, self.public_url, self.admin_url, self.internal_url,
            self.enabled, self.is_global, self.admin_token)
        self.assertStatusCode(201, resp, content)

        obj = json.loads(content)
        self.assertIsNotNone(obj['endpointTemplate']['id'], (resp, content))

        resp, _content = common.create_endpoint_xml(self.tenant_id,
            obj['endpointTemplate']['id'], self.admin_token)
        self.assertStatusCode(201, resp, content)

        resp, content = common.delete_endpoint_template(
            obj['endpointTemplate']['id'], self.admin_token)
        self.assertStatusCode(204, resp, content)

    def test_create_endpoint_template_xml(self):
        resp, content = common.create_endpoint_template_xml(
            self.region, self.service, self.public_url, self.admin_url,
            self.internal_url, self.enabled, self.is_global, self.admin_token)
        self.assertStatusCode(201, resp, content)

        #verify content
        dom = etree.Element("root")
        dom.append(etree.fromstring(content))
        endpoint_template = dom.find(
            "{http://docs.openstack.org/identity/api/v2.0}endpointTemplate")
        self.assertIsNotNone(endpoint_template, (resp, content))
        self.assertIsNotNone(endpoint_template.get("id"), (resp, content))
        self.assertEqual(endpoint_template.get("serviceId"), self.service_id, (resp, content))

        resp, content = common.delete_endpoint_template(
            endpoint_template.get("id"), self.admin_token)
        self.assertStatusCode(204, resp, content)

    def test_create_endpoint_template_using_service_admin_token(self):
        resp, content = common.create_endpoint_template(
            self.region, self.service, self.public_url, self.admin_url,
            self.internal_url, self.enabled, self.is_global,
            self.service_token)
        self.assertStatusCode(201, resp, content)

        obj = json.loads(content)
        self.assertIsNotNone(obj["endpointTemplate"], (resp, content))
        self.assertIsNotNone(obj["endpointTemplate"]['id'], (resp, content))
        self.assertEqual(obj["endpointTemplate"]['serviceId'], self.service_id, (resp, content))

        resp, content = common.delete_endpoint_template(
            obj["endpointTemplate"]['id'], self.service_token)
        self.assertStatusCode(204, resp, content)


class GetEndpointTemplatesTest(EndpointTemplatesTest):
    def test_get_endpoint_templates(self):
        header = httplib2.Http(".cache")
        url = '%sendpointTemplates' % (common.URL_V2)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": self.admin_token})
        self.assertStatusCode(200, resp, content)

        #verify content
        obj = json.loads(content)
        if not "endpointTemplates" in obj:
            raise self.fail("Expecting endpointTemplates")

    def test_get_endpoint_templates_using_service_admin_token(self):
        header = httplib2.Http(".cache")
        url = '%sendpointTemplates' % (common.URL_V2)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/json",
                                         "X-Auth-Token": self.service_token})
        self.assertEqual(200, int(resp['status']))

        #verify content
        obj = json.loads(content)
        if not "endpointTemplates" in obj:
            raise self.fail("Expecting endpointTemplates")

    def test_get_endpoint_templates_using_expired_auth_token(self):
        header = httplib2.Http(".cache")
        url = '%sendpointTemplates' % (common.URL_V2)
        #test for Content-Type = application/json
        resp, _content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/json",
                                         "X-Auth-Token": self.exp_auth_token})
        self.assertEqual(403, int(resp['status']))

    def test_get_endpoint_templates_using_disabled_auth_token(self):
        header = httplib2.Http(".cache")
        url = '%sendpointTemplates' % (common.URL_V2)
        #test for Content-Type = application/json
        resp, _content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/json",
                                         "X-Auth-Token": self.disabled_token})
        self.assertEqual(403, int(resp['status']))

    def test_get_endpoint_templates_using_missing_auth_token(self):
        header = httplib2.Http(".cache")
        url = '%sendpointTemplates' % (common.URL_V2)
        #test for Content-Type = application/json
        resp, _content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/json",
                                         "X-Auth-Token": self.missing_token})
        self.assertEqual(401, int(resp['status']))

    def test_get_endpoint_templates_using_invalid_auth_token(self):
        header = httplib2.Http(".cache")
        url = '%sendpointTemplates' % (common.URL_V2)
        #test for Content-Type = application/json
        resp, _content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/json",
                                         "X-Auth-Token": self.invalid_token})
        self.assertEqual(404, int(resp['status']))

    def test_get_endpoint_templates_xml(self):
        header = httplib2.Http(".cache")
        url = '%sendpointTemplates' % (common.URL_V2)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/xml",
                                         "X-Auth-Token": self.admin_token,
                                         "ACCEPT": "application/xml"})
        self.assertEqual(200, int(resp['status']))

        #verify content
        dom = etree.Element("root")
        dom.append(etree.fromstring(content))
        endpoint_templates = dom.find(
            "{http://docs.openstack.org/identity/api/v2.0}endpointTemplates")
        if endpoint_templates == None:
            self.fail("Expecting endpointTemplates")

    def test_get_endpoint_templates_xml_expired_auth_token(self):
        header = httplib2.Http(".cache")
        url = '%sendpointTemplates' % (common.URL_V2)
        #test for Content-Type = application/json
        resp, _content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/xml",
                                         "X-Auth-Token": self.exp_auth_token,
                                         "ACCEPT": "application/xml"})
        self.assertEqual(403, int(resp['status']))

    def test_get_endpoint_templates_xml_disabled_auth_token(self):
        header = httplib2.Http(".cache")
        url = '%sendpointTemplates' % (common.URL_V2)
        #test for Content-Type = application/json
        resp, _content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/xml",
                                         "X-Auth-Token": self.disabled_token,
                                         "ACCEPT": "application/xml"})
        self.assertEqual(403, int(resp['status']))

    def test_get_endpoint_templates_xml_missing_auth_token(self):
        header = httplib2.Http(".cache")
        url = '%sendpointTemplates' % (common.URL_V2)
        #test for Content-Type = application/json
        resp, _content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/xml",
                                         "X-Auth-Token": self.missing_token,
                                         "ACCEPT": "application/xml"})
        self.assertEqual(401, int(resp['status']))

    def test_get_endpoint_templates_xml_invalid_auth_token(self):
        header = httplib2.Http(".cache")
        url = '%sendpointTemplates' % (common.URL_V2)
        #test for Content-Type = application/json
        resp, _content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/xml",
                                         "X-Auth-Token": self.invalid_token,
                                         "ACCEPT": "application/xml"})
        self.assertEqual(404, int(resp['status']))


class GetEndpointTemplateTest(EndpointTemplatesTest):
    def test_get_endpoint(self):
        header = httplib2.Http(".cache")
        url = '%sendpointTemplates/%s' % (common.URL_V2, '1')
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/json",
                                         "X-Auth-Token": self.admin_token})
        #verify content
        obj = json.loads(content)
        if not "endpointTemplate" in obj:
            raise self.fail("Expecting endpointTemplate")

    def test_get_endpoint_using_service_admin_token(self):
        header = httplib2.Http(".cache")
        url = '%sendpointTemplates/%s' % (common.URL_V2, '1')
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/json",
                                         "X-Auth-Token": self.service_token})
        #verify content
        obj = json.loads(content)
        if not "endpointTemplate" in obj:
            raise self.fail("Expecting endpointTemplate")

    def test_get_endpoint_using_expired_auth_token(self):
        header = httplib2.Http(".cache")
        url = '%sendpointTemplates/%s' % (common.URL_V2, '1')
        #test for Content-Type = application/json
        resp, _content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/json",
                                         "X-Auth-Token": self.exp_auth_token})
        self.assertEqual(403, int(resp['status']))

    def test_get_endpoint_using_disabled_auth_token(self):
        header = httplib2.Http(".cache")
        url = '%sendpointTemplates/%s' % (common.URL_V2, '1')
        #test for Content-Type = application/json
        resp, _content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/json",
                                         "X-Auth-Token": self.disabled_token})
        self.assertEqual(403, int(resp['status']))

    def test_get_endpoint_using_missing_auth_token(self):
        header = httplib2.Http(".cache")
        url = '%sendpointTemplates/%s' % (common.URL_V2, '1')
        #test for Content-Type = application/json
        resp, _content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/json",
                                         "X-Auth-Token": self.missing_token})
        self.assertEqual(401, int(resp['status']))

    def test_get_endpoint_using_invalid_auth_token(self):
        header = httplib2.Http(".cache")
        url = '%sendpointTemplates/%s' % (common.URL_V2, '1')
        #test for Content-Type = application/json
        resp, _content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/json",
                                         "X-Auth-Token": self.invalid_token})
        self.assertEqual(404, int(resp['status']))

    def test_get_endpoint_xml(self):
        header = httplib2.Http(".cache")
        url = '%sendpointTemplates/%s' % (common.URL_V2, '1')
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}',
                                  headers={"Content-Type": "application/xml",
                                         "X-Auth-Token": self.admin_token,
                                         "ACCEPT": "application/xml"})
        self.assertEqual(200, int(resp['status']))

        #verify content
        dom = etree.Element("root")
        dom.append(etree.fromstring(content))
        endpoint = dom.find("{http://docs.openstack.org/identity/api/v2.0}" \
            "endpointTemplate")
        if endpoint == None:
            self.fail("Expecting endpointTemplate")


class UpdateEndpointTemplateTest(EndpointTemplatesTest):
    def test_update_endpoint(self):
        resp, content = common.update_endpoint_template(
            self.endpoint_template_id,
            self.region, self.service, self.public_url,
            self.admin_url, self.internal_url,
            False, self.is_global, self.admin_token)
        #verify content
        self.assertEqual(201, int(resp['status']))
        obj = json.loads(content)
        if not "endpointTemplate" in obj:
            raise self.fail("Expecting endpointTemplate")
        endpoint_template = obj["endpointTemplate"]
        if not "enabled" in endpoint_template:
            enabled = None
        else:
            enabled = endpoint_template["enabled"]
        self.assertFalse(enabled, "Expecting 'enabled' to be false.")

    def test_update_endpoint_xml(self):
        resp, content = common.update_endpoint_template_xml(
            self.endpoint_template_id,
            self.region, self.service, self.public_url,
            self.admin_url, self.internal_url,
            False, self.is_global, self.admin_token)
        #verify content
        self.assertEqual(201, int(resp['status']))
        dom = etree.Element("root")
        dom.append(etree.fromstring(content))
        endpoint_template = dom.find(
            "{http://docs.openstack.org/identity/api/v2.0}" \
            "endpointTemplate")
        if endpoint_template == None:
            self.fail("Expecting endpointTemplate")
        enabled = endpoint_template.get("enabled")
        self.assertFalse(enabled, "Expecting 'enabled' to be false.")

    def test_update_endpoint_using_service_admin_token(self):
        resp, content = common.update_endpoint_template(
            self.endpoint_template_id,
            self.region, self.service, self.public_url,
            self.admin_url, self.internal_url,
            False, self.is_global, self.service_token)
        #verify content
        self.assertEqual(201, int(resp['status']))
        obj = json.loads(content)
        if not "endpointTemplate" in obj:
            raise self.fail("Expecting endpointTemplate")
        endpoint_template = obj["endpointTemplate"]
        if not "enabled" in endpoint_template:
            enabled = None
        else:
            enabled = endpoint_template["enabled"]
        self.assertFalse(enabled, "Expecting 'enabled' to be false.")

    def test_update_endpoint_xml_using_service_admin_token(self):
        resp, content = common.update_endpoint_template_xml(
            self.endpoint_template_id,
            self.region, self.service, self.public_url,
            self.admin_url, self.internal_url,
            False, self.is_global, self.service_token)
        #verify content
        self.assertEqual(201, int(resp['status']))
        dom = etree.Element("root")
        dom.append(etree.fromstring(content))
        endpoint_template = dom.find(
            "{http://docs.openstack.org/identity/api/v2.0}" \
            "endpointTemplate")
        if endpoint_template == None:
            self.fail("Expecting endpointTemplate")
        enabled = endpoint_template.get("enabled")
        self.assertFalse(enabled, "Expecting 'enabled' to be false.")

    def test_update_endpoint_failure_cases(self):
        resp, content = common.update_endpoint_template(
            self.endpoint_template_id,
            self.region, self.service, self.public_url,
            self.admin_url, self.internal_url,
            self.enabled, self.is_global, self.disabled_token)
        self.assertEqual(403, int(resp['status']))
        resp, content = common.update_endpoint_template(
            self.endpoint_template_id,
            self.region, self.service, self.public_url,
            self.admin_url, self.internal_url,
            self.enabled, self.is_global, self.missing_token)
        self.assertEqual(401, int(resp['status']))
        resp, content = common.update_endpoint_template(
            self.endpoint_template_id,
            self.region, self.service, self.public_url,
            self.admin_url, self.internal_url,
            self.enabled, self.is_global, self.exp_auth_token)
        self.assertEqual(403, int(resp['status']))
        resp, content = common.update_endpoint_template(
            self.endpoint_template_id,
            self.region, self.service, self.public_url,
            self.admin_url, self.internal_url,
            self.enabled, self.is_global, self.invalid_token)
        self.assertEqual(404, int(resp['status']))
        #Update a NonExistent endpoint template.
        resp, content = common.update_endpoint_template(-1,
            self.region, self.service, self.public_url,
            self.admin_url, self.internal_url,
            self.enabled, self.is_global, self.admin_token)
        self.assertEqual(404, int(resp['status']))


class CreateEndpointRefsTest(EndpointTemplatesTest):
    def test_endpoint_create_json_using_expired_token(self):
        _header = httplib2.Http(".cache")
        resp, _content = common.create_endpoint(self.tenant, "1",
            str(self.exp_auth_token))
        resp_val = int(resp['status'])
        self.assertEqual(403, resp_val)

    def test_endpoint_create_json_using_disabled_token(self):
        _header = httplib2.Http(".cache")
        resp, _content = common.create_endpoint(self.tenant, "1",
            str(self.disabled_token))
        resp_val = int(resp['status'])
        self.assertEqual(403, resp_val)

    def test_endpoint_create_json_using_missing_token(self):
        _header = httplib2.Http(".cache")
        resp, _content = common.create_endpoint(self.tenant, "1",
            str(self.missing_token))
        resp_val = int(resp['status'])
        self.assertEqual(401, resp_val)

    def test_endpoint_create_json_using_invalid_token(self):
        _header = httplib2.Http(".cache")
        resp, _content = common.create_endpoint(self.tenant, "1",
            str(self.invalid_token))
        resp_val = int(resp['status'])
        self.assertEqual(404, resp_val)

    def test_endpoint_create_json(self):
        _header = httplib2.Http(".cache")
        common.delete_endpoint(
            self.tenant, "1", self.admin_token)
        resp, _content = common.create_endpoint(self.tenant, "1",
            self.admin_token)
        resp_val = int(resp['status'])
        self.assertEqual(201, resp_val)
        resp, _content = common.delete_endpoint(
            self.tenant, '1', self.admin_token)
        resp_val = int(resp['status'])
        self.assertEqual(204, resp_val)

    def test_endpoint_create_using_service_admin_token(self):
        _header = httplib2.Http(".cache")
        resp, _content = common.create_endpoint(self.tenant, "1",
            str(self.service_token))
        resp_val = int(resp['status'])
        self.assertEqual(201, resp_val)
        resp, _content = common.delete_endpoint(
            self.tenant, '1', self.service_token)
        resp_val = int(resp['status'])
        self.assertEqual(204, resp_val)

    def test_endpoint_create_xml(self):
        header = httplib2.Http(".cache")
        resp, _content = common.create_endpoint_xml(self.tenant, "1",
            self.admin_token)
        resp_val = int(resp['status'])
        self.assertEqual(201, resp_val)
        resp, _content = common.delete_endpoint(
            self.tenant, '1', self.admin_token)
        resp_val = int(resp['status'])
        self.assertEqual(204, resp_val)

    def test_endpoint_create_xml_using_expired_token(self):
        header = httplib2.Http(".cache")

        resp, _content = common.create_endpoint_xml(self.tenant, "1",
            self.admin_token)
        resp_val = int(resp['status'])
        self.assertEqual(201, resp_val)
        url = '%stenants/%s/endpoints/%s' % (common.URL_V2, self.tenant, '1')
        resp, _content = header.request(url, "DELETE", body='', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": str(self.exp_auth_token)})
        resp_val = int(resp['status'])
        self.assertEqual(403, resp_val)

    def test_endpoint_create_xml_using_disabled_token(self):
        header = httplib2.Http(".cache")

        resp, _content = common.create_endpoint_xml(self.tenant, "1",
            self.admin_token)
        resp_val = int(resp['status'])
        self.assertEqual(201, resp_val)
        url = '%stenants/%s/endpoints/%s' % (common.URL_V2, self.tenant, '1')
        resp, _content = header.request(url, "DELETE", body='', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": str(self.disabled_token)})
        resp_val = int(resp['status'])
        self.assertEqual(403, resp_val)

    def test_endpoint_create_xml_using_missing_token(self):
        header = httplib2.Http(".cache")

        resp, _content = common.create_endpoint_xml(self.tenant, "1",
            self.admin_token)
        resp_val = int(resp['status'])
        self.assertEqual(201, resp_val)
        url = '%stenants/%s/endpoints/%s' % (common.URL_V2, self.tenant, '1')
        resp, _content = header.request(url, "DELETE", body='', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": str(self.missing_token)})
        resp_val = int(resp['status'])
        self.assertEqual(401, resp_val)

    def test_endpoint_create_xml_using_invalid_token(self):
        header = httplib2.Http(".cache")

        resp, _content = common.create_endpoint_xml(self.tenant, "1",
            self.admin_token)
        resp_val = int(resp['status'])
        self.assertEqual(201, resp_val)
        url = '%stenants/%s/endpoints/%s' % (common.URL_V2, self.tenant, '1')
        resp, _content = header.request(url, "DELETE", body='', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": str(self.invalid_token)})
        resp_val = int(resp['status'])
        self.assertEqual(404, resp_val)


class GetEndPointTest(EndpointTemplatesTest):
    def test_get_endpoint_xml(self):
        header = httplib2.Http(".cache")
        url = '%stenants/%s/endpoints' % (common.URL_V2, self.tenant)
        #test for Content-Type = application/xml
        resp, _content = header.request(url, "GET", body='{}', headers={
            "Content-Type": "application/xml",
            "X-Auth-Token": self.admin_token,
            "ACCEPT": "application/xml"})
        self.assertEqual(200, int(resp['status']))

    def test_get_endpoint_xml_using_expired_auth_token(self):
        header = httplib2.Http(".cache")
        url = '%stenants/%s/endpoints' % (common.URL_V2, self.tenant)
        #test for Content-Type = application/xml
        resp, _content = header.request(url, "GET", body='{}', headers={
            "Content-Type": "application/xml",
            "X-Auth-Token": str(self.exp_auth_token),
            "ACCEPT": "application/xml"})
        self.assertEqual(403, int(resp['status']))

    def test_get_endpoint_xml_using_disabled_auth_token(self):
        header = httplib2.Http(".cache")
        url = '%stenants/%s/endpoints' % (common.URL_V2, self.tenant)
        #test for Content-Type = application/xml
        resp, _content = header.request(url, "GET", body='{}', headers={
            "Content-Type": "application/xml",
            "X-Auth-Token": str(self.disabled_token),
            "ACCEPT": "application/xml"})
        self.assertEqual(403, int(resp['status']))

    def test_get_endpoint_xml_using_missing_auth_token(self):
        header = httplib2.Http(".cache")
        url = '%stenants/%s/endpoints' % (common.URL_V2, self.tenant)
        #test for Content-Type = application/xml
        resp, _content = header.request(url, "GET", body='{}', headers={
            "Content-Type": "application/xml",
            "X-Auth-Token": str(self.missing_token),
            "ACCEPT": "application/xml"})
        self.assertEqual(401, int(resp['status']))

    def test_get_endpoint_xml_using_invalid_auth_token(self):
        header = httplib2.Http(".cache")
        url = '%stenants/%s/endpoints' % (common.URL_V2, self.tenant)
        #test for Content-Type = application/xml
        resp, _content = header.request(url, "GET", body='{}', headers={
            "Content-Type": "application/xml",
            "X-Auth-Token": str(self.invalid_token),
            "ACCEPT": "application/xml"})
        self.assertEqual(404, int(resp['status']))

    def test_get_endpoint_json(self):
        header = httplib2.Http(".cache")
        url = '%stenants/%s/endpoints' % (common.URL_V2, self.tenant)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": self.admin_token,
            "ACCEPT": "application/json"})
        self.assertEqual(200, int(resp['status']))
        obj = json.loads(content)
        if not "endpoints" in obj:
            raise self.fail("Expecting endpoints")

    def test_get_endpoint_json_using_expired_auth_token(self):
        header = httplib2.Http(".cache")
        url = '%stenants/%s/endpoints' % (common.URL_V2, self.tenant)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}',
            headers={"Content-Type": "application/json",
                "X-Auth-Token": str(self.exp_auth_token),
                "ACCEPT": "application/json"})
        self.assertEqual(403, int(resp['status']))
        _obj = json.loads(content)

    def test_get_endpoint_json_using_disabled_auth_token(self):
        header = httplib2.Http(".cache")
        url = '%stenants/%s/endpoints' % (common.URL_V2, self.tenant)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": str(self.disabled_token),
            "ACCEPT": "application/json"})
        self.assertEqual(403, int(resp['status']))
        _obj = json.loads(content)

    def test_get_endpoint_json_using_missing_auth_token(self):
        header = httplib2.Http(".cache")
        url = '%stenants/%s/endpoints' % (common.URL_V2, self.tenant)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": str(self.missing_token),
            "ACCEPT": "application/json"})
        self.assertEqual(401, int(resp['status']))
        _obj = json.loads(content)

    def test_get_endpoint_json_using_invalid_auth_token(self):
        header = httplib2.Http(".cache")
        url = '%stenants/%s/endpoints' % (common.URL_V2, self.tenant)
        #test for Content-Type = application/json
        resp, content = header.request(url, "GET", body='{}', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": str(self.invalid_token),
            "ACCEPT": "application/json"})
        self.assertEqual(404, int(resp['status']))
        _obj = json.loads(content)


class DeleteEndpointsTest(EndpointTemplatesTest):
    def test_delete_endpoint(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_endpoint(self.tenant, "1",
            self.admin_token)
        resp_val = int(resp['status'])
        self.assertEqual(201, resp_val)
        obj = json.loads(content)
        self.assertIsNotNone(obj["endpoint"]['id'], (resp, content))

        url = '%stenants/%s/endpoints/%s' % (common.URL_V2, self.tenant, obj["endpoint"]['id'])
        resp, content = header.request(url, "DELETE", body='', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": self.admin_token})
        resp_val = int(resp['status'])
        self.assertEqual(204, resp_val)

    def test_delete_endpoint_using_expired_auth_token(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_endpoint(self.tenant, "1",
            self.admin_token)
        resp_val = int(resp['status'])
        self.assertEqual(201, resp_val)
        obj = json.loads(content)
        self.assertIsNotNone(obj["endpoint"]['id'], (resp, content))
        url = '%stenants/%s/endpoints/%s' % (common.URL_V2, self.tenant, obj["endpoint"]['id'])
        resp, content = header.request(url, "DELETE", body='', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": str(self.exp_auth_token)})
        resp_val = int(resp['status'])
        self.assertEqual(403, resp_val)

    def test_delete_endpoint_using_disabled_auth_token(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_endpoint(self.tenant, "1",
            self.admin_token)
        resp_val = int(resp['status'])
        self.assertEqual(201, resp_val)
        obj = json.loads(content)
        self.assertIsNotNone(obj["endpoint"]['id'], (resp, content))
        url = '%stenants/%s/endpoints/%s' % (common.URL_V2, self.tenant, obj["endpoint"]['id'])
        resp, content = header.request(url, "DELETE", body='', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": str(self.disabled_token)})
        resp_val = int(resp['status'])
        self.assertEqual(403, resp_val)

    def test_delete_endpoint_using_missing_auth_token(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_endpoint(self.tenant, "1",
            self.admin_token)
        resp_val = int(resp['status'])
        self.assertEqual(201, resp_val)
        obj = json.loads(content)
        self.assertIsNotNone(obj["endpoint"]['id'], (resp, content))
        url = '%stenants/%s/endpoints/%s' % (common.URL_V2, self.tenant, obj["endpoint"]['id'])
        resp, content = header.request(url, "DELETE", body='', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": str(self.missing_token)})
        resp_val = int(resp['status'])
        self.assertEqual(401, resp_val)

    def test_delete_endpoint_using_invalid_auth_token(self):
        header = httplib2.Http(".cache")
        resp, content = common.create_endpoint(self.tenant, "1",
            self.admin_token)
        resp_val = int(resp['status'])
        self.assertEqual(201, resp_val)
        obj = json.loads(content)
        self.assertIsNotNone(obj["endpoint"]['id'], (resp, content))
        url = '%stenants/%s/endpoints/%s' % (common.URL_V2, self.tenant, obj["endpoint"]['id'])
        resp, content = header.request(url, "DELETE", body='', headers={
            "Content-Type": "application/json",
            "X-Auth-Token": str(self.invalid_token)})
        resp_val = int(resp['status'])
        self.assertEqual(404, resp_val)


if __name__ == '__main__':
    unittest.main()
