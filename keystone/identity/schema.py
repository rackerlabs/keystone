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

from keystone.common import validation
from keystone.common.validation import parameter_types


_user_properties = {
    'default_project_id': parameter_types.id_string,
    'description': validation.nullable(parameter_types.description),
    'domain_id': parameter_types.id_string,
    'email': validation.nullable(parameter_types.email),
    'enabled': parameter_types.boolean,
    'name': {
        'type': 'string',
        'minLength': 1,
        'maxLength': 64
    },
    'password': {
        'type': ['string', 'null'],
        'minLength': 1,
        # NOTE(lbragstad): the max length of this value should be read in
        # from the CONF.identity.max_password_length property, but we hit the
        # import order issue.
        'maxLength': 4096
    }
}

user_create = {
    'type': 'object',
    'properties': _user_properties,
    'required': ['name'],
    'additionalProperties': True
}

user_update = {
    'type': 'object',
    'properties': _user_properties,
    'minProperties': 1,
    'additionalProperties': True
}

_group_properties = {
    'description': validation.nullable(parameter_types.description),
    'domain_id': parameter_types.id_string,
    'name': {
        'type': 'string',
        'minLength': 1,
        'maxLength': 64
    }
}

group_create = {
    'type': 'object',
    'properties': _group_properties,
    'required': ['name'],
    'additionalProperties': True
}

group_update = {
    'type': 'object',
    'properties': _group_properties,
    'minProperties': 1,
    'additionalProperties': True
}
