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


resource_paths = [
    '/projects/{project_id}/users/{user_id}/roles/{role_id}',
    '/projects/{project_id}/groups/{group_id}/roles/{role_id}',
    '/domains/{domain_id}/users/{user_id}/roles/{role_id}',
    '/domains/{domain_id}/groups/{group_id}/roles/{role_id}',
]


resource_paths += ['/OS-INHERIT' + path + '/inherited_to_projects'
                   for path in resource_paths]


collection_paths = [
    '/projects/{project_id}/users/{user_id}/roles',
    '/projects/{project_id}/groups/{group_id}/roles',
    '/domains/{domain_id}/users/{user_id}/roles',
    '/domains/{domain_id}/groups/{group_id}/roles',
    ('/OS-INHERIT/domains/{domain_id}/groups/{group_id}/roles/'
     'inherited_to_projects'),
    ('/OS-INHERIT/domains/{domain_id}/users/{user_id}/roles/'
     'inherited_to_projects')
]


def get_operations(paths, method):
    return [{'path': '/v3' + path, 'method': method} for path in paths]


grant_policies = [
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'check_grant',
        check_str=base.RULE_ADMIN_REQUIRED,
        description='Check grant.',
        operations=get_operations(resource_paths, 'HEAD')),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'list_grants',
        check_str=base.RULE_ADMIN_REQUIRED,
        description='List grants.',
        operations=get_operations(collection_paths, 'GET')),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'create_grant',
        check_str=base.RULE_ADMIN_REQUIRED,
        description='Create grant.',
        operations=get_operations(resource_paths, 'PUT')),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'revoke_grant',
        check_str=base.RULE_ADMIN_REQUIRED,
        description='Revoke grant.',
        operations=get_operations(resource_paths, 'DELETE'))
]


def list_rules():
    return grant_policies
