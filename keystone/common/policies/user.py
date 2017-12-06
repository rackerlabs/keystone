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
        # A system administrator should be able to get a user reference for
        # anyone in the system. A user without a role assignment on the system
        # should be able to get references for users within the project their
        # token is scoped to, or their own user. The second case is likely a
        # "scope" check that keystone is going to have to enforce in code.
        scope_types=['system', 'project'],
        description='Show user details.',
        operations=[{'path': '/v3/users/{user_id}',
                     'method': 'GET'},
                    {'path': '/v3/users/{user_id}',
                     'method': 'HEAD'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'list_users',
        check_str=base.RULE_ADMIN_REQUIRED,
        # An administrator with a role assignment on the system should be able
        # to list all users. An administrator with a role assignment on a
        # project should only be able to list user within the project their
        # token is scoped to.
        scope_types=['system', 'project'],
        description='List users.',
        operations=[{'path': '/v3/users',
                     'method': 'GET'},
                    {'path': '/v3/users',
                     'method': 'HEAD'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'list_projects_for_user',
        check_str='',
        # This is somewhere in-between a project-level API and a system-level
        # API. It doesn't make sense for users to have roles on the system in
        # order to figure out what projects they are members of. At the same
        # time, it doesn't make sense to require a project-scoped token to
        # figure out what projects you have access to. This is likely an API
        # that is best enforced in code, which makes sense because all you need
        # to use this API is a valid token and it can be either system-scoped
        # or project-scoped.
        scope_types=['system', 'project'],
        description=('List all projects a user has access to via role '
                     'assignments.'),
        operations=[{'path': ' /v3/auth/projects',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'list_domains_for_user',
        check_str='',
        # This is somewhere in-between a project-level API and a system-level
        # API. It doesn't make sense for users to have roles on the system in
        # order to figure out what domains they are members of. At the same
        # time, it doesn't make sense to require a project-scoped token to
        # figure out what domains you have access to. This is likely an API
        # that is best enforced in code, which makes sense because all you need
        # to use this API is a valid token and it can be either system-scoped
        # or project-scoped.
        scope_types=['system', 'project'],
        description=('List all domains a user has access to via role '
                     'assignments.'),
        operations=[{'path': '/v3/auth/domains',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'create_user',
        check_str=base.RULE_ADMIN_REQUIRED,
        # This can be considered either a system-level policy or a
        # project-level policy. If this API is called with a system-scoped
        # token, then the user is owned by the system as a system-level
        # resource under whatever domain was specified in the request. If the
        # API is called with a project-scoped token by a project administrator,
        # the user should be created with the domain of the project
        # administrator. The second case is likely going to require a coded
        # "scope" check in keystone to work properly.  The same is true for the
        # following two APIs.
        scope_types=['system', 'project'],
        description='Create a user.',
        operations=[{'path': '/v3/users',
                     'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'update_user',
        check_str=base.RULE_ADMIN_REQUIRED,
        scope_types=['system', 'project'],
        description='Update a user, including administrative password resets.',
        operations=[{'path': '/v3/users/{user_id}',
                     'method': 'PATCH'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'delete_user',
        check_str=base.RULE_ADMIN_REQUIRED,
        scope_types=['system', 'project'],
        description='Delete a user.',
        operations=[{'path': '/v3/users/{user_id}',
                     'method': 'DELETE'}])
]


def list_rules():
    return user_policies
