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

from oslo_policy import policy

from keystone.common.policies import base

credential_policies = [
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'get_credential',
        check_str=base.RULE_ADMIN_REQUIRED,
        # Credentials aren't really project-scoped or system-scoped. Instead,
        # they are tied to a user. So does a user need a project-scoped or
        # system-scoped token to interact with them? Not sure what the right
        # answer is here. It seems like management of this resource is best
        # handled in code anyway. If this API is called with a system-scoped
        # token, it's a system-administrator and they should be able to get any
        # credential. If this API is called with a project-scoped token, then
        # extra enforcement needs to happen based on who created the
        # credential, what projects they are members of, and the project the
        # token is scoped to.
        scope_types=['system', 'project'],
        description='Show credentials details.',
        operations=[{'path': '/v3/credentials/{credential_id}',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'list_credentials',
        check_str=base.RULE_ADMIN_REQUIRED,
        # This one is tricky, too. An administrator with a system-scoped token
        # should be able to list all credentials. A user without a system role
        # assignment should be able to list their own credentials. The second
        # case is likely going to have to be enforced within keystone's
        # credential API logic as a "scope" check.
        scope_types=['system', 'project'],
        description='List credentials.',
        operations=[{'path': '/v3/credentials',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'create_credential',
        check_str=base.RULE_ADMIN_REQUIRED,
        # System administrators should be able to create credentials for
        # anyone. Users without system role assignments should only be able to
        # create credentials for themselves.
        scope_types=['system', 'project'],
        description='Create credential.',
        operations=[{'path': '/v3/credentials',
                     'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'update_credential',
        check_str=base.RULE_ADMIN_REQUIRED,
        # System adminstrators can update a credential for anyone. Users
        # without a role assignment on the system should only be able to update
        # their own credentials.
        scope_types=['system', 'project'],
        description='Update credential.',
        operations=[{'path': '/v3/credentials/{credential_id}',
                     'method': 'PATCH'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'delete_credential',
        check_str=base.RULE_ADMIN_REQUIRED,
        # System administrators should be able to delete any credential. Users
        # without a role assignment on the system should only be able to delete
        # credentials they created or have ownernship of.
        scope_types=['system', 'project'],
        description='Delete credential.',
        operations=[{'path': '/v3/credentials/{credential_id}',
                     'method': 'DELETE'}])
]


def list_rules():
    return credential_policies
