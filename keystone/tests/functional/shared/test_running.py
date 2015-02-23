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

import requests
import testtools
import testtools.matchers as M


http_status_codes = requests.status_codes.codes

admin_url = 'http://localhost:35357'
public_url = 'http://localhost:35357'


class TestBroken(testtools.TestCase):

    def test_admin_responds_with_multiple_choices(self):
        resp = requests.get(admin_url)
        self.assertThat(resp.status_code,
                        M.Equals(http_status_codes.multiple_choices))

    def test_public_responds_with_multiple_choices(self):
        resp = requests.get(public_url)
        self.assertThat(resp.status_code,
                        M.Equals(http_status_codes.multiple_choices))
