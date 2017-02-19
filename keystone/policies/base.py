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

IDENTITY = 'identity:%s'
RULE_ADMIN_REQUIRED = 'rule:admin_required'
RULE_ADMIN_OR_OWNER = 'rule:admin_or_owner'
RULE_ADMIN_OR_CREDENTIAL_OWNER = ('rule:admin_required or rule:owner and '
                                  'user_id:%(target.credential.user_id)s)')
RULE_ADMIN_OR_TARGET_DOMAIN = ('rule:admin_required or '
                               'token.project.domain.id:%(target.domain.id)s')
RULE_ADMIN_OR_TARGET_PROJECT = ('rule:admin_required or '
                                'project_id:%(target.project.id)s')


rules = [
    policy.RuleDefault('admin_required', 'role:admin or is_admin:1'),
    policy.RuleDefault('service_role', 'role:service'),
    policy.RuleDefault('service_or_admin',
                       'rule:admin_required or rule:service_role'),
    policy.RuleDefault('owner', 'user_id:%(user_id)s'),
    policy.RuleDefault('admin_or_owner', 'rule:admin_required or rule:owner'),
    policy.RuleDefault('token_subject', 'user_id:%(target.token.user_id)s'),
    policy.RuleDefault('admin_or_token_subject',
                       'rule:admin_required or rule:token_subject'),
    policy.RuleDefault('service_admin_or_token_subject',
                       'rule:service_or_admin or rule:token_subject'),
    policy.RuleDefault('default', 'rule:admin_required')
]


def list_rules():
    return rules
