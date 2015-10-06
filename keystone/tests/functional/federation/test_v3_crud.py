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
import uuid

from keystone.tests.functional import core as functests
from keystone.tests.functional.federation import fixtures


is_multiple_choices = testtools.matchers.Equals(
    requests.status_codes.codes.multiple_choices)
is_ok = testtools.matchers.Equals(requests.status_codes.codes.ok)
is_created = testtools.matchers.Equals(requests.status_codes.codes.created)
is_no_content = testtools.matchers.Equals(
    requests.status_codes.codes.no_content)

is_bad_request = testtools.matchers.Equals(
    requests.status_codes.codes.bad_request)
is_forbidden = testtools.matchers.Equals(requests.status_codes.codes.forbidden)
is_not_found = testtools.matchers.Equals(requests.status_codes.codes.not_found)

versions = ('v3',)


class IdentityProviderMixin(object):

    def _idp_url(self, id):
        return self.PUBLIC_URL + '/v3/OS-FEDERATION/identity_providers/' + id

    def idp_ref(self):
        return {
            'description': uuid.uuid4().hex,
            'remote_ids': [],
            'enabled': True
        }


class MappingMixin(object):

    def _mapping_url(self, id=''):
        return self.PUBLIC_URL + '/v3/OS-FEDERATION/mappings/' + id

    def mapping_ref(self):
        return {
            'rules': fixtures.MAPPING
        }


class TestIdentityProvider(functests.BaseTestCase, IdentityProviderMixin):

    def setUp(self):
        super(TestIdentityProvider, self).setUp()
        self.headers = self._http_headers(self.get_scoped_admin_token())

    def test_idp_crud(self):
        """Test Identity Provider CRUD operations.

        Test scenario:
        - Create IdP
        - Update IdP
            * description
            * enabled
            * remote_idps
        - Remove IdP
        - Make sure IdP does no longer exist in Keystone

        """
        idp_id = uuid.uuid4().hex
        idp_url = self._idp_url(idp_id)

        # create IdP
        idp = self.idp_ref()
        r_create = requests.put(idp_url, headers=self.headers,
                                json={'identity_provider': idp})
        self.assertThat(r_create.status_code, is_created)

        # get IdP
        r_get = requests.get(idp_url, headers=self.headers)
        self.assertThat(r_get.status_code, is_ok)

        # update IdP attributes

        idp['description'] = uuid.uuid4().hex
        idp['remote_ids'] = [uuid.uuid4().hex, uuid.uuid4().hex]
        idp['enabled'] = False
        r_update = requests.patch(idp_url, headers=self.headers,
                                  json={'identity_provider': idp})

        self.assertThat(r_update.status_code, is_ok)

        # delete IdP

        r_del = requests.delete(idp_url, headers=self.headers)
        self.assertThat(r_del.status_code, is_no_content)
        # make sure IdP no longer exists

        r_get = requests.get(idp_url, headers=self.headers)
        self.assertThat(r_get.status_code, is_not_found)

    def test_create_idp_default_values(self):
        """Try to create IdP without explicitely setting parameters."""

        idp_id = uuid.uuid4().hex
        idp_url = self._idp_url(idp_id)
        r = requests.put(idp_url, headers=self.headers,
                         json={'identity_provider': {}})

        self.assertThat(r.status_code, is_created)

    def test_rud_nonexistent_idp(self):
        """Test Identity Provider RUD operations on non existing object.

        Make sure Keystone correctly responds with HTTP 404 error.

        Test scenario:
        - Get non existing IdP
        - Update non existing IdP
        - Delete non existing IdP

        For each IdP id use random generated value.

        """
        idp_url = self._idp_url(uuid.uuid4().hex)
        r = requests.get(idp_url, headers=self.headers)
        self.assertThat(r.status_code, is_not_found)

        idp = self.idp_ref()

        r = requests.patch(idp_url, headers=self.headers,
                           json={'identity_provider': idp})
        self.assertThat(r.status_code, is_not_found)

        r = requests.delete(idp_url, headers=self.headers)
        self.assertThat(r.status_code, is_not_found)

    def test_create_idp_malformed_request(self):
        """Try creating Identity Provider with malformed request."""
        idp_url = self._idp_url(uuid.uuid4().hex)

        idp = {uuid.uuid4().hex: uuid.uuid4().hex for x in range(4)}
        r = requests.put(idp_url, headers=self.headers,
                         json={'identity_provider': idp})
        self.assertThat(r.status_code, is_forbidden)

    def test_update_idp_malformed_request(self):
        """Try updating Identity Provider with malformed request.

        Make sure the request will not be accepted.
        Test scenario:
        - Create Identity Provider
        - Update Identity Provider with malformed request
        - Ensure the request fails
        - Delete Identity Provider

        """
        idp_id = uuid.uuid4().hex
        idp_url = self._idp_url(idp_id)
        r = requests.put(idp_url, headers=self.headers,
                         json={'identity_provider': {}})

        self.assertThat(r.status_code, is_created)
        # try to update IdP with malformed request

        idp = {uuid.uuid4().hex: uuid.uuid4().hex for x in range(4)}

        r = requests.patch(idp_url, headers=self.headers,
                           json={'identity_provider': idp})

        self.assertThat(r.status_code, is_forbidden)


class TestMapping(functests.BaseTestCase, MappingMixin):

    def setUp(self):
        super(TestMapping, self).setUp()
        self.headers = self._http_headers(self.get_scoped_admin_token())

    def test_mapping_crud(self):
        """Test Mapping CRUD operations.

        Test scenario:
        - Create mapping
        - Update mapping
            * new mapping rules
        - Remove mapping
        - Make sure mapping does no longer exist in keystone

        """
        mapping_id = uuid.uuid4().hex
        mapping_url = self._mapping_url(mapping_id)

        # create mapping
        mapping = self.mapping_ref()
        r_create = requests.put(mapping_url, headers=self.headers,
                                json={'mapping': mapping})
        self.assertThat(r_create.status_code, is_created)

        # get mapping
        r_get = requests.get(mapping_url, headers=self.headers)
        self.assertThat(r_get.status_code, is_ok)

        # update mapping attributes
        r_update = requests.patch(mapping_url, headers=self.headers,
                                  json={'mapping': mapping})
        self.assertThat(r_update.status_code, is_ok)

        # delete mapping
        r_del = requests.delete(mapping_url, headers=self.headers)
        self.assertThat(r_del.status_code, is_no_content)

        # make sure mapping no longer exists
        r_get = requests.get(mapping_url, headers=self.headers)
        self.assertThat(r_get.status_code, is_not_found)

    def test_create_mapping_empty_input(self):
        """Try to create a mapping with empty input

        Expect HTTP 400 status code as server cannot accept requests without
        mapping rules.

        """
        mapping_id = uuid.uuid4().hex
        mapping_url = self._mapping_url(mapping_id)
        r = requests.put(mapping_url, headers=self.headers,
                         json={'mapping': {}})

        self.assertThat(r.status_code, is_bad_request)

    def test_rud_nonexistent_mapping(self):
        """Test mapping RUD operations on non existing object.

        Make sure Keystone correctly responds with HTTP 404 error.

        Test scenario:
        - Get non existing mapping
        - Update non existing mapping
        - Delete non existing mapping

        For each mapping id use random generated value.

        """
        mapping_url = self._mapping_url(uuid.uuid4().hex)
        r = requests.get(mapping_url, headers=self.headers)
        self.assertThat(r.status_code, is_not_found)

        mapping = self.mapping_ref()

        r = requests.patch(mapping_url, headers=self.headers,
                           json={'mapping': mapping})
        self.assertThat(r.status_code, is_not_found)

        r = requests.delete(mapping_url, headers=self.headers)
        self.assertThat(r.status_code, is_not_found)

    def test_create_mapping_malformed_request(self):
        """Try creating mapping with malformed request."""
        mapping_url = self._mapping_url(uuid.uuid4().hex)

        mapping = {uuid.uuid4().hex: uuid.uuid4().hex for x in range(4)}
        r = requests.put(mapping_url, headers=self.headers,
                         json={'mapping': mapping})
        self.assertThat(r.status_code, is_bad_request)

    def test_update_mapping_malformed_request(self):
        """Try updating mapping with malformed request.

        Make sure the request will not be accepted.
        Test scenario:
        - Create mapping
        - Update mapping with malformed request
        - Ensure the request fails
        - Delete mapping

        """
        mapping_id = uuid.uuid4().hex
        mapping_url = self._mapping_url(mapping_id)
        mapping = self.mapping_ref()
        r = requests.put(mapping_url, headers=self.headers,
                         json={'mapping': mapping})

        self.assertThat(r.status_code, is_created)

        # try to update mapping with malformed request
        mapping = {'rules': [uuid.uuid4().hex] for x in range(4)}

        r = requests.patch(mapping_url, headers=self.headers,
                           json={'mapping': mapping})

        self.assertThat(r.status_code, is_bad_request)
