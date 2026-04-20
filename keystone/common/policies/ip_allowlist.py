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

ADMIN_OR_DOMAIN_MANAGER = (
    '(' + base.RULE_ADMIN_REQUIRED + ') or '
    '(role:manager and token.domain.id:%(target.user.domain_id)s)'
)

ip_allowlist_policies = [
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'list_ip_allowlist_cidrs',
        check_str=base.RULE_ADMIN_OR_OWNER,
        scope_types=['system', 'project'],
        description='List IP allowlist CIDR entries for a user.',
        operations=[
            {
                'path': '/v3/OS-IP-ALLOWLIST/users/{user_id}/cidrs',
                'method': 'GET',
            },
        ],
    ),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'get_ip_allowlist_cidr',
        check_str=base.RULE_ADMIN_OR_OWNER,
        scope_types=['system', 'project'],
        description='Get a specific IP allowlist CIDR entry for a user.',
        operations=[
            {
                'path': '/v3/OS-IP-ALLOWLIST/users/{user_id}/cidrs/{entry_id}',
                'method': 'GET',
            },
        ],
    ),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'create_ip_allowlist_cidr',
        check_str=ADMIN_OR_DOMAIN_MANAGER,
        scope_types=['system', 'domain', 'project'],
        description='Create an IP allowlist CIDR entry for a user.',
        operations=[
            {
                'path': '/v3/OS-IP-ALLOWLIST/users/{user_id}/cidrs',
                'method': 'POST',
            },
        ],
    ),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'delete_ip_allowlist_cidr',
        check_str=ADMIN_OR_DOMAIN_MANAGER,
        scope_types=['system', 'domain', 'project'],
        description='Delete an IP allowlist CIDR entry for a user.',
        operations=[
            {
                'path': '/v3/OS-IP-ALLOWLIST/users/{user_id}/cidrs/{entry_id}',
                'method': 'DELETE',
            },
        ],
    ),
]


def list_rules():
    return ip_allowlist_policies
