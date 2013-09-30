# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
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

import testtools
from testtools import matchers

from keystone.tests import matchers as ksmatchers


class TestXMLEquals(testtools.TestCase):

    def test_equal_XML_passes(self):
        xml = """
            <?xml version="1.0" encoding="UTF-8"?>
            <test xmlns="http://docs.openstack.org/identity/api/v2.0">
                <success/>
            </test>
        """

        m = ksmatchers.XMLEquals(xml)
        self.assertThat(m.match(xml), matchers.Is(None))

    def test_equivalent_XML_passes(self):
        xml0 = """
            <?xml version="1.0" encoding="UTF-8"?>
            <test xmlns="http://docs.openstack.org/identity/api/v2.0">
                <success a="a" b="b"/>
            </test>
        """
        xml1 = """
            <?xml version="1.0" encoding="UTF-8"?>
            <test xmlns="http://docs.openstack.org/identity/api/v2.0">
                <success b="b" a="a"></success>
            </test>
        """

        m = ksmatchers.XMLEquals(xml0)
        self.assertThat(m.match(xml1), matchers.Is(None))

    def test_different_XML_fails(self):
        expected_xml = """
            <?xml version="1.0" encoding="UTF-8"?>
            <test xmlns="http://docs.openstack.org/identity/api/v2.0">
                <nope_it_fails/>
            </test>
        """
        other_xml = """
            <?xml version="1.0" encoding="UTF-8"?>
            <test xmlns="http://docs.openstack.org/identity/api/v2.0">
                <success/>
            </test>
        """

        m = ksmatchers.XMLEquals(expected_xml)
        mismatch = m.match(other_xml)
        self.assertThat(mismatch, matchers.Not(matchers.Is(None)))
