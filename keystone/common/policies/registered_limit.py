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

deprecated_update_registered_limit = policy.DeprecatedRule(
    name=base.IDENTITY % 'update_registered_limits',
    check_str=base.RULE_ADMIN_REQUIRED
)
deprecated_create_registered_limit = policy.DeprecatedRule(
    name=base.IDENTITY % 'create_registered_limits',
    check_str=base.RULE_ADMIN_REQUIRED
)
deprecated_delete_registered_limit = policy.DeprecatedRule(
    name=base.IDENTITY % 'delete_registered_limits',
    check_str=base.RULE_ADMIN_REQUIRED
)

DEPRECATED_REASON = """
As of the Stein release, the registered limit API now understands default
roles and system-scoped tokens, making the API more granular by default without
compromising security. The new policy defaults account for these changes
automatically. Be sure to take these new defaults into consideration if you are
relying on overrides in your deployment for the registered limit API.
"""

registered_limit_policies = [
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'get_registered_limit',
        check_str='',
        # Getting a single registered limit or listing all registered limits
        # should be information accessible to everyone. By setting
        # scope_types=['system', 'project'] we're making it so that anyone with
        # a role on the system or a project can obtain this information.
        # Making changes to a registered limit should be considered a protected
        # system-level API, as noted below with scope_types=['system'].
        scope_types=['system', 'project'],
        description='Show registered limit details.',
        operations=[{'path': '/v3/registered_limits/{registered_limit_id}',
                     'method': 'GET'},
                    {'path': '/v3/registered_limits/{registered_limit_id}',
                     'method': 'HEAD'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'list_registered_limits',
        check_str='',
        scope_types=['system', 'project'],
        description='List registered limits.',
        operations=[{'path': '/v3/registered_limits',
                     'method': 'GET'},
                    {'path': '/v3/registered_limits',
                     'method': 'HEAD'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'create_registered_limits',
        check_str='role:admin',
        scope_types=['system'],
        description='Create registered limits.',
        operations=[{'path': '/v3/registered_limits',
                     'method': 'POST'}],
        deprecated_rule=deprecated_create_registered_limit,
        deprecated_reason=DEPRECATED_REASON,
        deprecated_since=versionutils.deprecated.STEIN),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'update_registered_limit',
        check_str='role:member',
        scope_types=['system'],
        description='Update registered limit.',
        operations=[{'path': '/v3/registered_limits/{registered_limit_id}',
                     'method': 'PATCH'}],
        deprecated_rule=deprecated_update_registered_limit,
        deprecated_reason=DEPRECATED_REASON,
        deprecated_since=versionutils.deprecated.STEIN),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'delete_registered_limit',
        check_str='role:admin',
        scope_types=['system'],
        description='Delete registered limit.',
        operations=[{'path': '/v3/registered_limits/{registered_limit_id}',
                     'method': 'DELETE'}],
        deprecated_rule=deprecated_delete_registered_limit,
        deprecated_reason=DEPRECATED_REASON,
        deprecated_since=versionutils.deprecated.STEIN)
]


def list_rules():
    return registered_limit_policies
