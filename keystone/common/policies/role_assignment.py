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

role_assignment_policies = [
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'list_role_assignments',
        check_str=base.RULE_ADMIN_REQUIRED,
        # TODO(lbragstad): This API will behave differently depending on the
        # token scope used to call the API. With system-scoped token, this API
        # should return all role assignments. With a project-scoped token, it
        # should return only the role assignment relevant to the project the
        # token is scoped to. These checks are going to have to be encoded and
        # enforced in keystone code, since their behavior shouldn't change,
        # regardless of the deployment configuration.
        scope_types=['system', 'project'],
        description='List role assignments.',
        operations=[{'path': '/v3/role_assignments',
                     'method': 'GET'},
                    {'path': '/v3/role_assignments',
                     'method': 'HEAD'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'list_role_assignments_for_tree',
        check_str=base.RULE_ADMIN_REQUIRED,
        # This should be purely a project-scoped operation. The project tree
        # should be calculated based on the project the token used to make the
        # request is scoped to.
        scope_types=['project'],
        description=('List all role assignments for a given tree of '
                     'hierarchical projects.'),
        operations=[{'path': '/v3/role_assignments?include_subtree',
                     'method': 'GET'},
                    {'path': '/v3/role_assignments?include_subtree',
                     'method': 'HEAD'}])
]


def list_rules():
    return role_assignment_policies
