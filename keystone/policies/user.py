#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.


from keystone.policies import base
from oslo_policy import policy


ID = base.IDENTITY
RULE_AR = base.RULE_ADMIN_REQUIRED
RULE_AOO = base.RULE_ADMIN_OR_OWNER


rules = [
    policy.RuleDefault(ID % 'get_user', RULE_AOO),
    policy.RuleDefault(ID % 'list_users', RULE_AR),
    policy.RuleDefault(ID % 'create_user', RULE_AR),
    policy.RuleDefault(ID % 'update_user', RULE_AR),
    policy.RuleDefault(ID % 'delete_user', RULE_AR),
    policy.RuleDefault(ID % 'change_password', RULE_AOO),
]


def list_rules():
    return rules
