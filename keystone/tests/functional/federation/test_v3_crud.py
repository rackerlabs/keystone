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
import testtools.matchers

from keystone.tests.functional import core as functests


is_multiple_choices = testtools.matchers.Equals(
    requests.status_codes.codes.multiple_choices)
is_ok = testtools.matchers.Equals(requests.status_codes.codes.ok)

versions = ('v2.0', 'v3')


class TestIdentityProvider(functests.BaseTestCase):

    def _get_idp(self, id):
        pass

    def test_idp_crud(self):
        """Test Identity Provider CRUD operations.

        Test scenario:
        - Create IdP
        - Update IdP
            * description
            * enabled
            * [...]
        - Remove IdP
        - Make sure IdP does no longer exist in Keystone

        """
        pass

    def test_crud_nonexistent_idp(self):
        """Test Identity Provider CRUD operations on non existing object.

        Make sure Keystone correctly responds with HTTP 404 error.

        Test scenario:
        - Get non existing IdP
        - Update non existing IdP
        - Delete non existing IdP

        For each IdP id use random generated value.

        """
        pass

    def test_update_idp(self):
        """Test all combinations of Identity Provider updating.

        Test various combinations of different options updating.
        Test scenario:
        - Create Identity Provider
        - Disable Identity Provider
        - Enable Identity Provider
        - Update description attribute
        - Update 'remote_id' (what was that attr?)
        -

        """
        pass

    def test_create_idp_malformed_request(self):
        """Try creating Identity Provider with malformed request."""
        pass

    def test_update_idp_malformed_request(self):
        """Try updating Identity Provider with malformed request.

        Make sure the request will not be accepted.
        Test scenario:
        - Create Identity Provider
        - Update Identity Provider with malformed request
        - Ensure the request fails
        - Delete Identity Provider

        """
        pass
