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

domain_policies = [
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'get_domain',
        check_str=base.RULE_DEFAULT_DOMAIN_ADMIN,
        description='Show domain details.',
        operations=[{'path': '/v3/domains/{domain_id}',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'list_domains',
        check_str=base.RULE_DEFAULT_DOMAIN_ADMIN,
        description='List domains.',
        operations=[{'path': '/v3/domains',
                     'method': 'GET'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'create_domain',
        check_str=base.RULE_DEFAULT_DOMAIN_ADMIN,
        description='Create domain.',
        operations=[{'path': '/v3/domains',
                     'method': 'POST'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'update_domain',
        check_str=base.RULE_DEFAULT_DOMAIN_ADMIN,
        description='Update domain.',
        operations=[{'path': '/v3/domains/{domain_id}',
                     'method': 'PATCH'}]),
    policy.DocumentedRuleDefault(
        name=base.IDENTITY % 'delete_domain',
        check_str=base.RULE_DEFAULT_DOMAIN_ADMIN,
        description='Delete domain.',
        operations=[{'path': '/v3/domains/{domain_id}',
                     'method': 'DELETE'}])
]


def list_rules():
    return domain_policies
