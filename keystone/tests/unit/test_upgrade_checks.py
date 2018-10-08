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

from keystone.cmd import status
from keystone.tests import unit


class TestUpgradeChecks(unit.BaseTestCase):

    def test_successful_check(self):
        result = status.Checks().successful_noop()
        self.assertEqual(result.code, 0)
        self.assertEqual(result.details, 'Noop check was successful')

    def test_unsuccessful_check(self):
        result = status.Checks().unsuccessful_noop()
        self.assertEqual(result.code, 2)
        self.assertEqual(result.details, 'Noop check was unsuccessful')
