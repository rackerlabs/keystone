# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import uuid

from oslo_context import context
from oslo_policy import policy

from keystone.common import policies
import keystone.conf

CONF = keystone.conf.CONF

keystone.conf.configure()
keystone.conf.set_config_defaults()
CONF(project='keystone')


# enforcer = policy.Enforcer(CONF, use_conf=False)
enforcer = policy.Enforcer(CONF)
CONF.oslo_policy.enforce_scope = True
enforcer.register_defaults(policies.list_rules())

project = uuid.uuid4().hex
domain = uuid.uuid4().hex

result = {
    'System Administrator': {
        'ctxt': context.RequestContext(
            roles=['admin', 'member', 'reader'],
            system_scope='all'
        ),
        'operations': []
    },
    'System Member': {
        'ctxt': context.RequestContext(
            roles=['member', 'reader'],
            system_scope='all'
        ),
        'operations': []
    },
    'System Reader': {
        'ctxt': context.RequestContext(
            roles=['reader'],
            system_scope='all'
        ),
        'operations': []
    },
    'Domain Administrator': {
        'ctxt': context.RequestContext(
            roles=['admin', 'member', 'reader'],
            domain_id=domain
        ),
        'operations': []
    },
    'Domain Member': {
        'ctxt': context.RequestContext(
            roles=['member', 'reader'],
            domain_id=domain
        ),
        'operations': []
    },
    'Domain Reader': {
        'ctxt': context.RequestContext(
            roles=['reader'],
            domain_id=domain
        ),
        'operations': []
    },
    'Project Administrator': {
        'ctxt': context.RequestContext(
            roles=['admin', 'member', 'reader'],
            project_id=project
        ),
        'operations': []
    },
    'Project Member': {
        'ctxt': context.RequestContext(
            roles=['member', 'reader'],
            project_id=project
        ),
        'operations': []
    },
    'Project Reader': {
        'ctxt': context.RequestContext(
            roles=['reader'],
            project_id=project
        ),
        'operations': []
    },
}


for persona_name, persona in result.iteritems():

    for rule, v in enforcer.registered_rules.iteritems():
        target = {}
        try:
            if enforcer.enforce(rule, target, persona['ctxt']):
                persona['operations'].append(v)

        except policy.InvalidScope:
            continue
