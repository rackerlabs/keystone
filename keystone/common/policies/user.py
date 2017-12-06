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

user_policies = [
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'get_user',
        check_str=base.RULE_ADMIN_OR_OWNER,
        # FIXME(lbragstad): First, a system administrator should be able to get
        # a user reference for anyone in the system. Second, a project
        # administrator should be able to get references for users within the
        # project their token is scoped to or their domain. Third, a user
        # should be able to get a reference for themselves. This is going to
        # require keystone to be smarter about enforcing policy checks in code,
        # specifically for the last two cases. Once that is fixed, we can
        # uncomment the following line.
        # scope_types=['system', 'project'],
        description='Show user details.',
        operations=[{'path': '/v3/users/{user_id}',
                     'method': 'GET'},
                    {'path': '/v3/users/{user_id}',
                     'method': 'HEAD'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'list_users',
        check_str=base.RULE_ADMIN_REQUIRED,
        # FIXME(lbragstad): See the above comment about why this is commented
        # out.
        # scope_types=['system', 'project'],
        description='List users.',
        operations=[{'path': '/v3/users',
                     'method': 'GET'},
                    {'path': '/v3/users',
                     'method': 'HEAD'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'list_projects_for_user',
        check_str='',
        # NOTE(lbragstad): We explicitly omit scope_types from this policy
        # because it's meant to be called with an unscoped token, which doesn't
        # apply to scope_types or its purpose. So long as the user is in the
        # system and has a valid token, they should be able to generate a list
        # of projects they have access to.
        description=('List all projects a user has access to via role '
                     'assignments.'),
        operations=[{'path': ' /v3/auth/projects',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'list_domains_for_user',
        check_str='',
        # NOTE(lbragstad): We explicitly omit scope_types from this policy
        # because it's meant to be called with an unscoped token, which doesn't
        # apply to scope_types or its purpose. So long as the user is in the
        # system and has a valid token, they should be able to generate a list
        # of domains they have access to.
        description=('List all domains a user has access to via role '
                     'assignments.'),
        operations=[{'path': '/v3/auth/domains',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'create_user',
        check_str=base.RULE_ADMIN_REQUIRED,
        # FIXME(lbragstad): This can be considered either a system-level policy
        # or a project-level policy. System administrator should have the
        # ability to create users in any domain. Domain (or project)
        # administrators should have the ability to create users in the domain
        # they administer. The second case is going to require a policy check
        # in code. Until that happens, we will leave this policy as is, without
        # scope_types defined. Once keystone knows how to handle these calls
        # with various scopes we can specify scope types.
        # scope_types=['system', 'project'],
        description='Create a user.',
        operations=[{'path': '/v3/users',
                     'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'update_user',
        check_str=base.RULE_ADMIN_REQUIRED,
        # FIXME(lbragstad): See the above comment for why scope_types is
        # commented out.
        # scope_types=['system', 'project'],
        description='Update a user, including administrative password resets.',
        operations=[{'path': '/v3/users/{user_id}',
                     'method': 'PATCH'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'delete_user',
        check_str=base.RULE_ADMIN_REQUIRED,
        # FIXME(lbragstad): See the above comment for why scope_types is
        # commented out.
        # scope_types=['system', 'project'],
        description='Delete a user.',
        operations=[{'path': '/v3/users/{user_id}',
                     'method': 'DELETE'}])
]


def list_rules():
    return user_policies
