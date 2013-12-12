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

import uuid

from oslotest import mockpatch

from keystone.auth.plugins import oidc
from keystone.common import dependency
from keystone import config
from keystone.contrib.federation import controllers as federation_controllers
from keystone.tests import test_v3

CONF = config.CONF


@dependency.requires('federation_api')
class OpenIDTests(test_v3.RestfulTestCase):
    IDP_ID = 'BP'
    MAPPING_ID = 'BPMAP'
    PROTOCOL_ID = 'oidc'

    AUTH_METHOD = 'oidc'
    UNSCOPED_V3_OIDC_AUTH_REQ = {
        'identity': {
            'methods': [
                AUTH_METHOD
            ],
            AUTH_METHOD: {
                'user': 'user1',
                'password': 'security',
                'client_id': 'rp',
                'scope': 'openid email'
            }
        }
    }

    OIDC_CLAIM = {
        "nonce": "9c2b51b0ef3849828d6fedc8019eae2b",
        "sub": "stevemar@example.com",
        "at_hash": "RC3QNVOT1h31ofNyFlQskQ",
        "iss": "https://localhost:8020/oidc/v10/providers/OP",
        "groupIds": [
            "cn=Customer_Group,ou=memberlist,o=example.com",
            "cn=Example_Admin_Group,ou=memberlist,o=example.com",
            "cn=Example_All_Group,ou=memberlist,o=example.com"
        ],
        "exp": 1395358515,
        "iat": 1395354915,
        "aud": "rp"
    }

    def setUp(self):
        super(OpenIDTests, self).setUp()

        def fake_handshake(auth_plugin, auth_payload):
            return self.OIDC_CLAIM

        self.useFixture(mockpatch.PatchObject(oidc.OpenIdConnect,
                                              '_perform_handshake',
                                              fake_handshake))

    def load_fixtures(self, fixtures):
        super(OpenIDTests, self).load_fixtures(fixtures)
        self.load_federation_sample_data()

    def test_issue_unscoped_token(self):
        api = federation_controllers.Auth()
        context = {'environment': {}, 'query_string': []}
        r = api.federated_authentication(context, self.IDP_ID,
                                         self.PROTOCOL_ID,
                                         self.UNSCOPED_V3_OIDC_AUTH_REQ)
        self.assertIsNotNone(r.headers.get('X-Subject-Token'))

    def idp_ref(self, id=None):
        idp = {
            'id': id or uuid.uuid4().hex,
            'enabled': True,
            'description': uuid.uuid4().hex
        }
        return idp

    def proto_ref(self, id=None, mapping_id=None):
        proto = {
            'id': id or uuid.uuid4().hex,
            'mapping_id': mapping_id or uuid.uuid4().hex
        }
        return proto

    def mapping_ref(self, id=None, rules=None):
        return {
            'id': id or uuid.uuid4().hex,
            'rules': rules or self.rules['rules']
        }

    def load_federation_sample_data(self):
        """Inject additional data."""

        # Create and add domains
        self.domainA = self.new_domain_ref()
        self.assignment_api.create_domain(self.domainA['id'],
                                          self.domainA)

        # Create and add projects
        self.proj_admin = self.new_project_ref(domain_id=self.domainA['id'])
        self.assignment_api.create_project(self.proj_admin['id'],
                                           self.proj_admin)
        self.proj_customer = self.new_project_ref(domain_id=self.domainA['id'])
        self.assignment_api.create_project(self.proj_customer['id'],
                                           self.proj_customer)

        # Create and add groups
        self.group_customers = self.new_group_ref(domain_id=self.domainA['id'])
        self.identity_api.create_group(self.group_customers['id'],
                                       self.group_customers)
        self.group_admins = self.new_group_ref(
            domain_id=self.domainA['id'])
        self.identity_api.create_group(self.group_admins['id'],
                                       self.group_admins)

        # Create and add roles
        self.role_customer = self.new_role_ref()
        self.assignment_api.create_role(self.role_customer['id'],
                                        self.role_customer)
        self.role_admin = self.new_role_ref()
        self.assignment_api.create_role(self.role_admin['id'],
                                        self.role_admin)

        # Customers can access
        # * proj_customer
        self.assignment_api.create_grant(self.role_customer['id'],
                                         group_id=self.group_customers['id'],
                                         project_id=self.proj_customer['id'])

        # Admins can access:
        # * proj_customer
        # * proj_admin
        self.assignment_api.create_grant(self.role_admin['id'],
                                         group_id=self.group_admins['id'],
                                         project_id=self.proj_customer['id'])
        self.assignment_api.create_grant(self.role_admin['id'],
                                         group_id=self.group_admins['id'],
                                         project_id=self.proj_admin['id'])

        self.rules = {
            "rules": [
                {
                    "local": [
                        {
                            "user": {
                                "name": "{0}"
                            }
                        }
                    ],
                    "remote": [
                        {
                            "type": "sub"
                        }
                    ]
                },
                {
                    "local": [
                        {
                            "group": {
                                "id": self.group_customers['id']
                            }
                        }
                    ],
                    "remote": [
                        {
                            "type": "REMOTE_GROUP",
                            "regex": True,
                            "any_one_of": [
                                ".*Customer_Group*"
                            ]
                        }
                    ]
                },
                {
                    "local": [
                        {
                            "group": {
                                "id": self.group_admins['id']
                            }
                        }
                    ],
                    "remote": [
                        {
                            "type": "REMOTE_GROUP",
                            "regex": True,
                            "any_one_of": [
                                ".*Admin_Group*"
                            ]
                        }
                    ]
                }
            ]
        }

        # Add IDP
        self.idp = self.idp_ref(id=self.IDP_ID)
        self.federation_api.create_idp(self.idp['id'], self.idp)

        # Add a mapping
        self.mapping = self.mapping_ref(id=self.MAPPING_ID)
        self.federation_api.create_mapping(self.mapping['id'], self.mapping)

        # Add protocol
        self.proto_saml = self.proto_ref(id=self.PROTOCOL_ID,
                                         mapping_id=self.mapping['id'])
        self.federation_api.create_protocol(self.idp['id'],
                                            self.proto_saml['id'],
                                            self.proto_saml)
