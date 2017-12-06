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

project_policies = [
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'get_project',
        # FIXME(lbragstad): The default check_str here should change to be just
        # a role. The OR_TARGET_PROJECT bit of this check_str should actually
        # be moved into keystone. If this API is called with a project-scoped
        # token, keystone should check to make sure they match, which means we
        # can move the logic into code and not have it configurable via policy.
        check_str=base.RULE_ADMIN_OR_TARGET_PROJECT,
        scope_types=['system', 'project'],
        description='Show project details.',
        operations=[{'path': '/v3/projects/{project_id}',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'list_projects',
        # FIXME(lbragstad): If this API is called with a system-scoped token,
        # all projects should be returned. If it is called with a
        # project-scoped token, only projects relevant to that project's
        # position in the hierarchy should be returned.
        check_str=base.RULE_ADMIN_REQUIRED,
        scope_types=['system', 'project'],
        description='List projects.',
        operations=[{'path': '/v3/projects',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'list_user_projects',
        check_str=base.RULE_ADMIN_OR_OWNER,
        # FIXME(lbragstad): This feels like a system-level API. What should
        # happen if a someone attempts to list their projects with a
        # project-scoped token?
        scope_types=['system'],
        description='List projects for user.',
        operations=[{'path': '/v3/users/{user_id}/projects',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'create_project',
        check_str=base.RULE_ADMIN_REQUIRED,
        # FIXME(lbragstad): If this API is called with a project-scoped token,
        # keystone should enforce project hierarchies based on the token scope
        # used in the request. That should be something coded into keystone and
        # not left up to configuration via policy.
        scope_types=['system', 'project'],
        description='Create project.',
        operations=[{'path': '/v3/projects',
                     'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'update_project',
        check_str=base.RULE_ADMIN_REQUIRED,
        # FIXME(lbragstad): If this API is called with a project-scoped token,
        # keystone should enforce project hierarchies based on the token scope
        # used in the request. That should be coded into keystone and not left
        # up to configuration via policy.
        scope_types=['system', 'project'],
        description='Update project.',
        operations=[{'path': '/v3/projects/{project_id}',
                     'method': 'PATCH'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'delete_project',
        check_str=base.RULE_ADMIN_REQUIRED,
        # FIXME(lbragstad): If this API is called with a project-scoped token,
        # keystone should enforce project hierarchies based on the token scope
        # used in the request. That should be something coded into keystone and
        # not left up to configuration via policy.
        scope_types=['system', 'project'],
        description='Delete project.',
        operations=[{'path': '/v3/projects/{project_id}',
                     'method': 'DELETE'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'list_project_tags',
        check_str=base.RULE_ADMIN_OR_TARGET_PROJECT,
        # This should be a system-level policy and a project-level policy.
        # System users should be able to tag projects. Project administrator
        # should be able to tag projects within their hierarchy.
        scope_types=['system', 'project'],
        description='List tags for a project.',
        operations=[{'path': '/v3/projects/{project_id}/tags',
                     'method': 'GET'},
                    {'path': '/v3/projects/{project_id}/tags',
                     'method': 'HEAD'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'get_project_tag',
        check_str=base.RULE_ADMIN_OR_TARGET_PROJECT,
        scope_types=['system', 'project'],
        description='Check if project contains a tag.',
        operations=[{'path': '/v3/projects/{project_id}/tags/{value}',
                     'method': 'GET'},
                    {'path': '/v3/projects/{project_id}/tags/{value}',
                     'method': 'HEAD'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'update_project_tags',
        check_str=base.RULE_ADMIN_REQUIRED,
        scope_types=['system', 'project'],
        description='Replace all tags on a project with the new set of tags.',
        operations=[{'path': '/v3/projects/{project_id}/tags',
                     'method': 'PUT'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'create_project_tag',
        check_str=base.RULE_ADMIN_REQUIRED,
        scope_types=['system', 'project'],
        description='Add a single tag to a project.',
        operations=[{'path': '/v3/projects/{project_id}/tags/{value}',
                     'method': 'PUT'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'delete_project_tags',
        check_str=base.RULE_ADMIN_REQUIRED,
        scope_types=['system', 'project'],
        description='Remove all tags from a project.',
        operations=[{'path': '/v3/projects/{project_id}/tags',
                     'method': 'DELETE'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'delete_project_tag',
        check_str=base.RULE_ADMIN_REQUIRED,
        scope_types=['system', 'project'],
        description='Delete a specified tag from project.',
        operations=[{'path': '/v3/projects/{project_id}/tags/{value}',
                     'method': 'DELETE'}])
]


def list_rules():
    return project_policies
