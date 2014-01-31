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

import urllib
import uuid

from keystone.common import dependency
from keystone.contrib import federation


@dependency.requires('assignment_api', 'identity_api',
                     'token_api', 'token_provider_api')
class FederationFixtures(object):

    ASSERTION = {
        'ADFS_LOGIN': 'madenis',
        'ADFS_NAME': 'M',
        'ADFS_SURNAME': 'D',
        'ADFS_ORG': 'BIG_ORG',
        'ADFS_DEP': 'IT'
    }
    IDP = 'ORGANISATION_IDP'
    PROTOCOL = 'saml2'
    USER = 'marek@ORGANISATION_IDP'
    ENC_USER = urllib.quote(USER)

    def new_ref(self):
        """Populates a ref with attributes common to all API entities."""
        return {
            'id': uuid.uuid4().hex,
            'name': uuid.uuid4().hex,
            'description': uuid.uuid4().hex,
            'enabled': True}

    def new_domain_ref(self):
        """Populates a ref with attributes common to all API entities."""
        return self.new_ref()

    def new_project_ref(self, domain_id):
        ref = self.new_ref()
        ref['domain_id'] = domain_id
        return ref

    def new_group_ref(self, domain_id):
        ref = self.new_ref()
        ref['domain_id'] = domain_id
        return ref

    def new_role_ref(self):
        return self.new_ref()

    def load_federation_sample_data(self):
        """Inject additional data.

        Prepare:
        - 3 domains
        - 3 projects
        - 3 groups assertion will map to

        """
        self.domainA = self.new_domain_ref()
        self.assignment_api.create_domain(self.domainA['id'],
                                          self.domainA)
        self.domainB = self.new_domain_ref()
        self.assignment_api.create_domain(self.domainB['id'],
                                          self.domainB)
        self.domainC = self.new_domain_ref()
        self.assignment_api.create_domain(self.domainC['id'],
                                          self.domainC)

        self.domain_ids = {}
        self.domain_ids['DOMAIN_A'] = [self.domainA['id']]
        self.domain_ids['DOMAIN_B'] = [self.domainB['id']]
        self.domain_ids['DOMAIN_C'] = [self.domainC['id']]
        self.domain_ids['DOMAIN_AB'] = [self.domainA['id'],
                                        self.domainB['id']]
        self.domain_ids['DOMAIN_AC'] = [self.domainA['id'],
                                        self.domainC['id']]
        self.domain_ids['DOMAIN_BC'] = [self.domainB['id'],
                                        self.domainC['id']],
        self.domain_ids['DOMAIN_ALL'] = [self.domainA['id'],
                                         self.domainB['id'],
                                         self.domainC['id']]

        self.projectA = self.new_project_ref(domain_id=self.domainA['id'])
        self.assignment_api.create_project(self.projectA['id'],
                                           self.projectA)
        self.projectB = self.new_project_ref(domain_id=self.domainA['id'])
        self.assignment_api.create_project(self.projectB['id'],
                                           self.projectB)
        self.projectC = self.new_project_ref(domain_id=self.domainA['id'])
        self.assignment_api.create_project(self.projectC['id'],
                                           self.projectC)

        self.project_ids = {}
        self.project_ids['PROJ_A'] = [self.projectA['id']]
        self.project_ids['PROJ_B'] = [self.projectB['id']]
        self.project_ids['PROJ_C'] = [self.projectC['id']]
        self.project_ids['PROJ_AC'] = [self.projectA['id'],
                                       self.projectC['id']]
        self.project_ids['PROJ_ALL'] = [self.projectA['id'],
                                        self.projectB['id'],
                                        self.projectC['id']]

        self.group1 = self.new_group_ref(
            domain_id=self.domainA['id'])
        self.identity_api.create_group(self.group1['id'], self.group1)

        self.group2 = self.new_group_ref(
            domain_id=self.domainA['id'])
        self.identity_api.create_group(self.group2['id'], self.group2)

        self.group3 = self.new_group_ref(
            domain_id=self.domainA['id'])
        self.identity_api.create_group(self.group3['id'], self.group3)

        self.role1 = self.new_role_ref()
        self.assignment_api.create_role(self.role1['id'], self.role1)
        self.role2 = self.new_role_ref()
        self.assignment_api.create_role(self.role2['id'], self.role2)
        self.role3 = self.new_role_ref()
        self.assignment_api.create_role(self.role3['id'], self.role3)

        # assign roles to projects
        self.assignment_api.create_grant(self.role1['id'],
                                         group_id=self.group1['id'],
                                         project_id=self.projectA['id'])

        self.assignment_api.create_grant(self.role2['id'],
                                         group_id=self.group2['id'],
                                         project_id=self.projectB['id'])
        # role 3 assigns group3 to projects AA and AC.
        self.assignment_api.create_grant(self.role3['id'],
                                         group_id=self.group3['id'],
                                         project_id=self.projectA['id'])
        self.assignment_api.create_grant(self.role3['id'],
                                         group_id=self.group3['id'],
                                         project_id=self.projectC['id'])

        # assign roles to domain
        self.assignment_api.create_grant(self.role1['id'],
                                         group_id=self.group1['id'],
                                         domain_id=self.domainA['id'])
        self.assignment_api.create_grant(self.role2['id'],
                                         group_id=self.group2['id'],
                                         domain_id=self.domainB['id'])

        self.assignment_api.create_grant(self.role3['id'],
                                         group_id=self.group3['id'],
                                         domain_id=self.domainA['id'])
        self.assignment_api.create_grant(self.role3['id'],
                                         group_id=self.group3['id'],
                                         domain_id=self.domainC['id'])

        # generate fake tokens
        context = {'environment': {}}

        api = federation.controllers.AuthController()
        self.tokens = {}
        VARIANTS = ('PROJ_A', 'PROJ_B', 'PROJ_AC', 'PROJ_ALL',
                    'DOMAIN_A', 'DOMAIN_B', 'DOMAIN_AC', 'DOMAIN_ALL')
        for variant in VARIANTS:
            self._inject_mapped_groups(context, variant)
            r = api.authenticate(context, self.IDP, self.PROTOCOL)
            self.tokens[variant] = r.headers.get('X-Subject-Token')

        self.TOKEN_INPUT_B_FROM_B = {
            "auth": {
                "identity": {
                    "methods": [
                        "federation"
                    ],
                    "federation": {
                        "id": self.tokens['PROJ_B']
                    }
                },
                "scope": {
                    "project": {
                        "id": self.project_ids['PROJ_B']
                    }
                }

            }
        }

        self.TOKEN_INPUT_B_FROM_WRONG_TOKEN = {
            "auth": {
                "identity": {
                    "methods": [
                        "federation"
                    ],
                    "federation": {
                        "id": uuid.uuid4().hex
                    }
                },
                "scope": {
                    "project": {
                        "id": self.project_ids['PROJ_B']
                    }
                }

            }
        }

        self.TOKEN_INPUT_PROJ_A_FROM_AC = {
            "auth": {
                "identity": {
                    "methods": [
                        "federation"
                    ],
                    "federation": {
                        "id": self.tokens['PROJ_AC']
                    }
                },
                "scope": {
                    "project": {
                        "id": self.project_ids['PROJ_A']
                    }
                }

            }
        }

        self.TOKEN_INPUT_PROJ_C_FROM_AC = {
            "auth": {
                "identity": {
                    "methods": [
                        "federation"
                    ],
                    "federation": {
                        "id": self.tokens['PROJ_AC']
                    }
                },
                "scope": {
                    "project": {
                        "id": self.project_ids['PROJ_C']
                    }
                }

            }
        }

        self.TOKEN_INPUT_PROJ_B_FROM_A = {
            "auth": {
                "identity": {
                    "methods": [
                        "federation"
                    ],
                    "federation": {
                        "id": self.tokens['PROJ_A']
                    }

                },
                "scope": {
                    "project": {
                        "id": self.project_ids['PROJ_B']
                    }
                }
            }
        }

    def _inject_mapped_groups(self, context, variant):
        """Inject mapped set of user/groups.
        This methods helps skipping assertion mapping step.

        :param context: request context

        """
        RULES = {
            'PROJ_ALL': {
                'group_ids': [
                    self.group1['id'],
                    self.group2['id'],
                    self.group3['id']
                ]
            },
            'PROJ_A': {
                'group_ids': [
                    self.group1['id']
                ]
            },
            'PROJ_B': {
                'group_ids': [
                    self.group2['id']
                ]
            },
            'PROJ_AC': {
                'group_ids': [
                    self.group3['id']
                ]
            },
            'DOMAIN_ALL': {
                'group_ids': [
                    self.group1['id'],
                    self.group2['id'],
                    self.group3['id']
                ]
            },
            'DOMAIN_A': {
                'group_ids': [
                    self.group1['id']
                ]
            },
            'DOMAIN_B': {
                'group_ids': [
                    self.group2['id']
                ]
            },
            'DOMAIN_AC': {
                'group_ids': [
                    self.group3['id']
                ]
            }

        }
        rules = RULES[variant]
        rules.setdefault('name', self.USER)
        context['environment']['mapped_rules'] = rules

    def _inject_assertion(self, context):
        context.setdefault('environment', {})
        context['environment'].update(self.ASSERTION)
