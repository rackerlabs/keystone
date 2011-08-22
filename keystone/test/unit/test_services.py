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
import json
from lxml import etree

from keystone.test.unit import common


class ServicesTest(common.FunctionalTest):
    def setUp(self, *args, **kwargs):
        super(ServicesTest, self).setUp(*args, **kwargs)

    def tearDown(self, *args, **kwargs):
        super(ServicesTest, self).tearDown(*args, **kwargs)


class GetServicesTest(ServicesTest):
    def test_get_services_using_keystone_admin_token_json(self):
        resp, content = common.get_services(self.admin_token)
        self.assertEqual(200, int(resp['status']))

        obj = json.loads(content)
        self.assertIsNotNone(obj['services']['values'], (resp, content))
        self.assertTrue(len(obj['services']), (resp, content))

        # is this the same as the below?
        self.assertIn(self.sample_service, [service['id'] for service in obj['services']], (resp, content))

        is_service_found = None
        for service in obj['services']:
            if service["id"] in [self.sample_service]:
                is_service_found = True
        if not is_service_found:
            raise self.fail("Service not found")

    def test_get_services_using_keystone_admin_token_xml(self):
        resp, content = common.get_services_xml(self.admin_token)
        self.assertEqual(200, int(resp['status']))
        # verify content
        # Validate Returned Content
        dom = etree.Element("root")
        dom.append(etree.fromstring(content))
        service_list = dom.find(
            "{http://docs.openstack.org/identity/api/v2.0}"
            "services")
        self.assertIsNotNone(service_list, (resp, content))

        services = service_list.findall(
            "{http://docs.openstack.org/identity/api/v2.0}"
            "service")
        self.assertTrue(len(services), (resp, content))

        for service in services:
            if service.get("id") in [self.sample_service]:
                is_service_found = True
        if not is_service_found:
            raise self.fail("Service not found")

    def test_get_services_using_service_admin_token(self):
        resp, content = common.get_services(self.service_token)
        self.assertEqual(200, int(resp['status']))
        #verify content
        obj = json.loads(content)
        if not "services" in obj:
            raise self.fail("Expecting Services")
        self.assertTrue(len(obj["services"]["values"]), (resp, content))

        is_service_found = None
        for service in obj["services"]["values"]:
            if service["id"] in [self.sample_service]:
                is_service_found = True
        if not is_service_found:
            raise self.fail("Service not found")

    def test_get_services_using_service_admin_token_xml(self):
        resp, content = common.get_services_xml(self.service_token)
        self.assertEqual(200, int(resp['status']))
        # Verify content
        # Validate Returned Content
        dom = etree.Element("root")
        dom.append(etree.fromstring(content))
        service_list = dom.find(
            "{http://docs.openstack.org/identity/api/v2.0}"
            "services")
        self.assertIsNotNone(service_list, (resp, content))

        services = service_list.findall(
            "{http://docs.openstack.org/identity/api/v2.0}"
            "service")
        self.assertTrue(len(services), (resp, content))

        for service in services:
            if service.get("id") in [self.sample_service]:
                is_service_found = True
        if not is_service_found:
            raise self.fail("Service not found")

    def test_get_services_using_invalid_tokens(self):
        resp, content = common.get_services(self.disabled_token)
        self.assertStatusCode(403, resp, content)
        resp, content = common.get_services(self.missing_token)
        self.assertStatusCode(401, resp, content)
        resp, content = common.get_services(self.exp_auth_token)
        self.assertStatusCode(403, resp, content)
        resp, content = common.get_services(self.invalid_token)
        self.assertStatusCode(404, resp, content)


class GetServiceTest(ServicesTest):
    def test_service_get_json(self):
        resp, content = common.get_service(
            self.sample_service, self.admin_token)
        self.assertStatusCode(200, resp, content)

    def test_service_get_xml(self):
        resp, content = common.get_service_xml(
            self.sample_service, self.admin_token)
        self.assertStatusCode(200, resp, content)

    def test_service_get_using_expired_token(self):
        resp, content = common.get_service(
            self.sample_service, str(self.exp_auth_token))
        self.assertStatusCode(403, resp, content)

    def test_service_get_using_disabled_token(self):
        resp, content = common.get_service(
            self.sample_service, self.disabled_token)
        self.assertStatusCode(403, resp, content)

    def test_service_get_json_using_missing_token(self):
        resp, content = common.get_service(
            self.sample_service, self.missing_token)
        self.assertStatusCode(401, resp, content)

    def test_service_get_json_using_invalid_token(self):
        resp, content = common.get_service(
            self.sample_service, self.invalid_token)
        self.assertStatusCode(404, resp, content)

    def test_get_service_using_invalid_tokens(self):
        resp, content = common.get_service(
            self.sample_service, self.disabled_token)
        self.assertStatusCode(403, resp, content)

        resp, content = common.get_service(
            self.sample_service, self.missing_token)
        self.assertStatusCode(401, resp, content)

        resp, content = common.get_service(
            self.sample_service, self.exp_auth_token)
        self.assertStatusCode(403, resp, content)

        resp, content = common.get_service(
            self.sample_service, self.invalid_token)
        self.assertStatusCode(404, resp, content)


class CreateServiceTest(ServicesTest):
    def test_service_create_json(self):
        resp, content = common.create_service(
            self.test_service, self.admin_token)
        self.assertStatusCode(201, resp, content)
        common.delete_service(self.test_service, self.admin_token)

    def test_service_create_xml(self):
        resp, content = common.create_service_xml(
            self.test_service, self.admin_token)
        self.assertStatusCode(201, resp, content)

    def test_service_create_duplicate_json(self):
        resp, content = common.create_service(
            self.test_service, self.admin_token)
        self.assertStatusCode(201, resp, content)
        resp, content = common.create_service(
            self.test_service, self.admin_token)
        self.assertStatusCode(409, resp, content)
        common.delete_service(self.test_service, self.admin_token)

    def test_service_create_using_expired_token(self):
        resp, content = common.create_service(
            self.test_service, str(self.exp_auth_token))
        self.assertStatusCode(403, resp, content)

    def test_service_create_using_disabled_token(self):
        resp, content = common.create_service(
            self.test_service, self.disabled_token)
        self.assertStatusCode(403, resp, content)

    def test_service_create_json_using_missing_token(self):
        resp, content = common.create_service(
            self.test_service, self.missing_token)
        self.assertStatusCode(401, resp, content)

    def test_service_create_json_using_invalid_token(self):
        resp, content = common.create_service(self.test_service,
            self.invalid_token)
        self.assertStatusCode(404, resp, content)


class DeleteServiceTest(ServicesTest):
    def test_service_delete(self):
        resp, content = common.delete_service(
            self.test_service, self.admin_token)
        self.assertStatusCode(204, resp, content)

    def test_service_which_has_dependencies_delete(self):
        resp, content = common.create_service(
            self.test_service, self.admin_token)
        resp, content = common.create_role_mapped_to_service(
            self.test_service + ":test_role",
            self.admin_token, self.test_service)
        self.assertStatusCode(201, resp, content)
        resp, content = common.create_role_ref(
            self.user, self.test_service +
            ":test_role", self.tenant, self.admin_token)
        self.assertStatusCode(201, resp, content)
        resp, content = common.create_endpoint_template(\
            'DFW', self.test_service, 'public_url', \
            'admin_url', 'internal_url', True, False, self.admin_token)
        self.assertStatusCode(201, resp, content)

        #verify content
        obj = json.loads(content)
        self.assertIsNotNone(obj['endpointTemplate']['id'], (resp, content))

        resp, content = common.create_endpoint_xml(self.tenant,
            obj['endpointTemplate']['id'],
            self.admin_token)
        self.assertStatusCode(201, resp, content)

        resp, content = common.delete_service(
            self.test_service, self.admin_token)
        self.assertStatusCode(204, resp, content)

    def test_service_delete_json_using_expired_token(self):
        resp, content = common.delete_service(
            self.test_service, str(self.exp_auth_token))
        self.assertStatusCode(403, resp, content)

    def test_service_delete_json_using_disabled_token(self):
        resp, content = common.delete_service(
            self.test_service, self.disabled_token)
        self.assertStatusCode(403, resp, content)

    def test_service_delete_json_using_missing_token(self):
        resp, content = common.delete_service(
            self.test_service, self.missing_token)
        self.assertStatusCode(401, resp, content)

    def test_service_delete_json_using_invalid_token(self):
        resp, content = common.delete_service(
            self.test_service, self.invalid_token)
        self.assertStatusCode(404, resp, content)


if __name__ == '__main__':
    unittest.main()
