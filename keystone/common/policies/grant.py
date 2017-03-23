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

grant_resources = [
    {'path': '/v3/projects/{project_id}/users/{user_id}/roles/{role_id}'},
    {'path': '/v3/projects/{project_id}/groups/{group_id}/roles/{role_id}'},
    {'path': '/v3/domains/{domain_id}/users/{user_id}/roles/{role_id}'},
    {'path': '/v3/domains/{domain_id}/groups/{group_id}/roles/{role_id}'},
    {
        'path': ('/v3/OS-INHERIT/domains/{domain_id}/users/{user_id}/roles/'
                 '{role_id}/inherited_to_projects')
    },
    {
        'path': ('/v3/OS-INHERIT/domains/{domain_id}/groups/{group_id}/roles/'
                 '{role_id}/inherited_to_projects')
    },
    {
        'path': ('/v3/OS-INHERIT/projects/{project_id}/users/{user_id}/roles/'
                 '{role_id}/inherited_to_projects')
    },
    {
        'path': ('/v3/OS-INHERIT/projects/{project_id}/groups/{group_id}/'
                 'roles/{role_id}/inherited_to_projects')
    }
]

grant_collections = [
    {'path': '/v3/projects/{project_id}/users/{user_id}/roles'},
    {'path': '/v3/projects/{project_id}/groups/{group_id}/roles'},
    {'path': '/v3/domains/{domain_id}/users/{user_id}/roles'},
    {'path': '/v3/domains/{domain_id}/groups/{group_id}/role'},
    {
        'path': ('/v3/OS-INHERIT/domains/{domain_id}/groups/{group_id}/roles/'
                 'inherited_to_projects')
    },
    {
        'path': ('/v3/OS-INHERIT/domains/{domain_id}/users/{user_id}/roles/'
                 'inherited_to_projects')
    }
]


def get_operations(path_dic, method):
    operation = []

    for p in path_dic:
        p['method'] = method
        operation.append(p)

    return operation


grant_policies = [
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'check_grant',
        check_str=base.RULE_ADMIN_REQUIRED,
        description='Check grant.',
        operations=get_operations(grant_resources, 'HEAD')),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'list_grants',
        check_str=base.RULE_ADMIN_REQUIRED,
        description='List grants.',
        operations=get_operations(grant_collections, 'GET')),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'create_grant',
        check_str=base.RULE_ADMIN_REQUIRED,
        description='Create grant.',
        operations=get_operations(grant_resources, 'PUT')),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'revoke_grant',
        check_str=base.RULE_ADMIN_REQUIRED,
        description='Revoke grant.',
        operations=get_operations(grant_resources, 'DELETE'))
]


def list_rules():
    return grant_policies
