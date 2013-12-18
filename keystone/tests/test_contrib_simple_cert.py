# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

from keystone.tests import rest


class TestSimpleCert(rest.RestfulTestCase):

    def request_cert(self, path):
        content_type = 'application/x-pem-file'
        response = self.request(app=self.public_app,
                                method='GET',
                                path=path,
                                headers={'Accept': content_type},
                                expected_status=200)

        self.assertEqual(response.content_type, content_type)
        self.assertIn('---BEGIN', response.body)

        return response

    def test_ca_cert(self):
        self.request_cert('/v3/OS-SIMPLE-CERT/ca')

    def test_signing_cert(self):
        self.request_cert('/v3/OS-SIMPLE-CERT/certificates')
