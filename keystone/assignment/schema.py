# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from keystone.validation import common_parameter_types


create = {
    'type': 'object',
    'properties': {
        'name': common_parameter_types.name,
        'domain_id': common_parameter_types.uuid,
        'description': common_parameter_types.description,
        'enabled': common_parameter_types.boolean
    },
    # NOTE(lbragstad): A project name is the only parameter required for
    # project creation according to the Identity V3 API. We should think
    # about using the maxProperties validator here, and in update.
    'required': ['name'],
    'additionalProperties': True,
}

update = {
    'type': 'object',
    'properties': {
        'name': common_parameter_types.name,
        'domain_id': common_parameter_types.uuid,
        'description': common_parameter_types.description,
        'enabled': common_parameter_types.boolean
    },
    # NOTE(lbragstad) Make sure at least one property is being updated
    'minProperties': 1,
    'additionalProperties': True,
}

delete = {
    'type': 'object',
    # NOTE(lbragstad): Don't allow any parameters on delete
    'maxProperties': 0
}
