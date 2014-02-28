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

from keystone.common.validation import parameter_types


project_create = {
    'type': 'object',
    'properties': {
        'description': parameter_types.description,
        'domain_id': parameter_types.id_string,
        'enabled': parameter_types.boolean,
        'name': parameter_types.name
    },
    # NOTE(lbragstad): A project name is the only parameter required for
    # project creation according to the Identity V3 API. We should think
    # about using the maxProperties validator here, and in update.
    'required': ['name'],
    'additionalProperties': True
}

project_update = {
    'type': 'object',
    'properties': {
        'description': parameter_types.description,
        'domain_id': parameter_types.id_string,
        'enabled': parameter_types.boolean,
        'name': parameter_types.name
    },
    # NOTE(lbragstad) Make sure at least one property is being updated
    'minProperties': 1,
    'additionalProperties': True
}

domain_create = {
    'type': 'object',
    'properties': {
        'description': parameter_types.description,
        'enabled': parameter_types.boolean,
        'name': parameter_types.name
    },
    'required': ['name'],
    'additionalProperties': True
}

domain_update = {
    'type': 'object',
    'properties': {
        'description': parameter_types.description,
        'enabled': parameter_types.boolean,
        'name': parameter_types.name
    },
    'minProperties': 1,
    'additionalProperties': True
}

role_create = {
    'type': 'object',
    'properties': {
        'name': parameter_types.name
    },
    'required': ['name'],
    'additionalProperties': True
}

role_update = {
    'type': 'object',
    'properties': {
        'name': parameter_types.name
    },
    'minProperties': 1,
    'additionalProperties': True
}
