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

implied_role_policies = [
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'get_implied_role',
        check_str=base.RULE_ADMIN_REQUIRED,
        description=('Get information for an implied role associated with a '
                     'superior role.'),
        operations=[{'path': ('/v3/roles/{prior_role_id}/implies/'
                              '{implied_role_id}'),
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'list_implied_roles',
        check_str=base.RULE_ADMIN_REQUIRED,
        description='Get a list of implied roles for a superior prior.',
        operations=[{'path': '/v3/roles/{prior_role_id}/implies',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'create_implied_role',
        check_str=base.RULE_ADMIN_REQUIRED,
        description='Create role inference rule.',
        operations=[{'path': ('/v3/roles/{prior_role_id}/implies/'
                              '{implied_role_id}'),
                     'method': 'PUT'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'delete_implied_role',
        check_str=base.RULE_ADMIN_REQUIRED,
        description='Delete role inference rule.',
        operations=[{'path': ('/v3/roles/{prior_role_id}/implies/'
                              '{implied_role_id}'),
                     'method': 'DELETE'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'list_role_inference_rules',
        check_str=base.RULE_ADMIN_REQUIRED,
        description='List all role inference rules.',
        operations=[{'path': '/v3/role_inferences',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'check_implied_role',
        check_str=base.RULE_ADMIN_REQUIRED,
        description='Check role inference rule.',
        operations=[{'path': ('/v3/roles/{prior_role_id}/implies/'
                              '{implied_role_id}'),
                     'method': 'HEAD'}])
]


def list_rules():
    return implied_role_policies
