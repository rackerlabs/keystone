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
import unittest2 as unittest

from keystone.test.unit import common


class VersionTest(common.FunctionalTest):

    #Given _a_ to make inherited test cases in an order.
    #here to call below method will call as last test case

    def test_a_get_version_json(self):
        header = httplib2.Http(".cache")
        resp, content = header.request(common.URL_V2, "GET", body="",
                                  headers={"Content-Type": "application/json"})
        self.assertEqual(200, int(resp['status']))
        self.assertEqual('application/json', common.content_type(resp))

    def test_a_get_version_xml(self):
        header = httplib2.Http(".cache")
        resp, content = header.request(common.URL_V2, "GET", body="",
                                  headers={"Content-Type": "application/xml",
                                           "ACCEPT": "application/xml"})
        self.assertEqual(200, int(resp['status']))
        self.assertEqual('application/xml', common.content_type(resp))

if __name__ == '__main__':
    unittest.main()
