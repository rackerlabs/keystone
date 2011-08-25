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
import keystone.backends.api
import keystone.logic.types.fault as fault
import keystone.logic.service as service
import stubout


class TokenEndpointTest(unittest.TestCase):
    def _noop_validate_admin_token(self, admin_token):
        pass

    class FakeDtoken(object):
        expires = 'now'
        tenant_id = 1
        id = 2

    def _fake_token_get(self, token_id):
        return self.FakeDtoken()

    def _fake_missing_token_get(self, token_id):
        return None

    class FakeEndpoint(object):
        service = 'foo'

    def _fake_tenant_get_all_endpoints(self, tenant_id):
        return [self.FakeEndpoint()]

    def setUp(self):
        self.stubout = stubout.StubOutForTesting()

        self.identity = service.IdentityService()
        # The downside of python "private" methods ... you
        # have to do stuff like this to stub them out.
        self.stubout.SmartSet(self.identity,
                              "_IdentityService__validate_admin_token",
                              self._noop_validate_admin_token)

    def tearDown(self):
        self.stubout.SmartUnsetAll()
        self.stubout.UnsetAll()

    def test_endpoints_from_good_token(self):
        """Happy Day scenario."""
        self.stubout.SmartSet(keystone.backends.api.TOKEN,
                              'get', self._fake_token_get)

        self.stubout.SmartSet(keystone.backends.api.BaseTenantAPI,
                              'get_all_endpoints',
                              self._fake_tenant_get_all_endpoints)

        auth_data = self.identity.get_endpoints_for_token("admin token",
                                                          "token id")
        self.assertEquals(auth_data.base_urls[0].service, 'foo')
        self.assertEquals(len(auth_data.base_urls), 1)

    def test_endpoints_from_bad_token(self):
        self.stubout.SmartSet(keystone.backends.api.TOKEN,
                              'get', self._fake_missing_token_get)

        self.assertRaises(fault.ItemNotFoundFault,
                          self.identity.get_endpoints_for_token,
                          "admin token", "token id")


if __name__ == '__main__':
    unittest.main()
