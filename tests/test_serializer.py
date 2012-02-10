# vim: tabstop=4 shiftwidth=4 softtabstop=4

import re

from keystone.common import serialize
from keystone import test


class XmlSerializerTestCase(test.TestCase):
    def assertEqualIgnoreWhitespace(self, a, b):
        """Splits two strings into lists and compares them.

        This provides easy-to-read failures from nose.

        """
        a = re.sub('[ \n]+', ' ', a).strip().split()
        b = re.sub('[ \n]+', ' ', b).strip().split()
        self.assertEqual(a, b)

    def test_auth_request(self):
        d = {
            "auth": {
                "passwordCredentials": {
                    "username": "test_user",
                    "password": "mypass"
                },
                "tenantName": "customer-x"
            }
        }

        actual = serialize.to_xml(d)

        self.assertEqualIgnoreWhitespace(actual, """
            <?xml version="1.0" encoding="UTF-8"?>
            <auth xmlns="http://docs.openstack.org/identity/api/v2.0"
                    tenantName="customer-x">
                <passwordCredentials
                        username="test_user"
                        password="mypass"/>
            </auth>
        """)

    def test_role_crud(self):
        d = {
            "role": {
                "id": "123",
                "name": "Guest",
                "description": "Guest Access"
            }
        }

        actual = serialize.to_xml(d)

        # TODO(dolph): examples show this description as an attribute?
        self.assertEqualIgnoreWhitespace(actual, """
            <?xml version="1.0" encoding="UTF-8"?>
            <role xmlns="http://docs.openstack.org/identity/api/v2.0"
                    id="123"
                    name="Guest">
                <description>Guest Access</description>
            </role>
        """)

    def test_service_crud(self):
        d = {
            # FIXME(dolph): should be...
            # "OS-KSADM:service": {
            "service": {
                "id": "123",
                "name": "nova",
                "type": "compute",
                "description": "OpenStack Compute Service"
            }
        }

        xmlns="http://docs.openstack.org/identity/api/ext/OS-KSADM/v1.0"
        actual = serialize.to_xml(d, xmlns=xmlns)

        # TODO(dolph): examples show this description as an attribute?
        self.assertEqualIgnoreWhitespace(actual, """
            <?xml version="1.0" encoding="UTF-8"?>
            <service
                    xmlns="%(xmlns)s"
                    type="compute"
                    id="123"
                    name="nova">
                <description>OpenStack Compute Service</description>
            </service>
        """ % {'xmlns': xmlns})

    def test_tenant_crud(self):
        d = {
            "tenant": {
                "id": "1234",
                "name": "ACME corp",
                "description": "A description...",
                "enabled": True
            }
        }
        actual = serialize.to_xml(d)

        self.assertEqualIgnoreWhitespace(actual, """
            <?xml version="1.0" encoding="UTF-8"?>
            <tenant
                    xmlns="http://docs.openstack.org/identity/api/v2.0"
                    enabled="true"
                    id="1234"
                    name="ACME corp">
                <description>A description...</description>
            </tenant>
        """)
