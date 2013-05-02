# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack LLC
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

import test_content_types
import default_fixtures


class RestfulTestCase(test_content_types.RestfulTestCase):

    def setUp(self, load_sample_data=True):
        super(RestfulTestCase, self).setUp()

        self.load_backends()

        if load_sample_data:
            self.load_fixtures(default_fixtures)

            # TODO(termie): is_admin is being deprecated once the policy stuff
            #               is all working
            # TODO(termie): add an admin user to the fixtures and use that user

            # override the fixtures, for now
            self.metadata_foobar = self.identity_api.update_metadata(
                self.user_foo['id'],
                self.tenant_bar['id'],
                dict(roles=[self.role_admin['id']], is_admin='1'))

    def get_scoped_token(self):
        """Convenience method so that we can test authenticated requests."""
        r = self.public_request(
            method='POST',
            path='/v2.0/tokens',
            body={
                'auth': {
                    'passwordCredentials': {
                        'username': self.user_foo['name'],
                        'password': self.user_foo['password'],
                    },
                    'tenantId': self.tenant_bar['id'],
                },
            })
        return self._get_token_id(r)

    def _get_token_id(self, r):
        """Helper method to return a token ID from a response.

        This needs to be overridden by child classes for on their content type.

        """
        raise NotImplementedError()
