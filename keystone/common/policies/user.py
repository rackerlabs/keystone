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

from oslo_log import versionutils
from oslo_policy import policy

from keystone.common.policies import base

DEPRECATED_REASON = (
    'As of the Stein release, the user API understands how to handle '
    'system-scoped tokens in addition to project and domain tokens, making '
    'the API more accessible to users without compromising security or '
    'manageability for administrators. The new default policies for this API '
    'account for these changes automatically.'
)

deprecated_get_user = policy.DeprecatedRule(
    name=base.IDENTITY % 'get_user',
    check_str=base.RULE_ADMIN_OR_OWNER
)
deprecated_list_users = policy.DeprecatedRule(
    name=base.IDENTITY % 'list_users',
    check_str=base.RULE_ADMIN_OR_OWNER
)

user_policies = [
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'get_user',
        check_str=(
            '(role:reader and system_scope:all) or '
            '(role:reader and token.domain.id:%(target.user.domain_id)s) or '
            'user_id:%(target.user.id)s'
        ),
        scope_types=['system', 'domain', 'project'],
        description='Show user details.',
        operations=[{'path': '/v3/users/{user_id}',
                     'method': 'GET'},
                    {'path': '/v3/users/{user_id}',
                     'method': 'HEAD'}],
        deprecated_rule=deprecated_get_user,
        deprecated_reason=DEPRECATED_REASON,
        deprecated_since=versionutils.deprecated.STEIN),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'list_users',
        check_str='(role:reader and system_scope:all) or role:reader',
        scope_types=['system', 'domain'],
        description='List users.',
        operations=[{'path': '/v3/users',
                     'method': 'GET'},
                    {'path': '/v3/users',
                     'method': 'HEAD'}],
        deprecated_rule=deprecated_list_users,
        deprecated_reason=DEPRECATED_REASON,
        deprecated_since=versionutils.deprecated.STEIN),
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
        # in code. Until that happens, we will leave this as a system-level
        # policy.
        scope_types=['system', 'domain'],
        description='Create a user.',
        operations=[{'path': '/v3/users',
                     'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'update_user',
        check_str=base.RULE_ADMIN_REQUIRED,
        # FIXME(lbragstad): See the above comment about adding support for
        # project scope_types in the future.
        scope_types=['system', 'domain'],
        description='Update a user, including administrative password resets.',
        operations=[{'path': '/v3/users/{user_id}',
                     'method': 'PATCH'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'delete_user',
        check_str=base.RULE_ADMIN_REQUIRED,
        # FIXME(lbragstad): See the above comment about adding support for
        # project scope_types in the future.
        scope_types=['system', 'domain'],
        description='Delete a user.',
        operations=[{'path': '/v3/users/{user_id}',
                     'method': 'DELETE'}])
]


def list_rules():
    return user_policies
