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

from keystone.policies import base

token_revocation_policies = [
    policy.RuleDefault(name=base.IDENTITY % 'check_token',
                       check_str='rule:admin_or_token_subject'),
    policy.RuleDefault(name=base.IDENTITY % 'validate_token',
                       check_str='rule:service_admin_or_token_subject'),
    policy.RuleDefault(name=base.IDENTITY % 'validate_token_head',
                       check_str='rule:service_or_admin'),
    policy.RuleDefault(name=base.IDENTITY % 'revocation_list',
                       check_str='rule:service_or_admin'),
    policy.RuleDefault(name=base.IDENTITY % 'revoke_token',
                       check_str='rule:admin_or_token_subject')
]


def list_rules():
    return token_revocation_policies
