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


_domain_properties = {
    'type': 'object',
    'properties': {
        'name': parameter_types.name,
        'id': parameter_types.id_string
    },
    'additionalProperties': False
}

_project_properties = {
    'type': 'object',
    'properties': {
        'name': parameter_types.name,
        'id': parameter_types.id_string,
        'domain': _domain_properties
    },
    'additionalProperties': False
}

_user_properties = {
    'type': 'object',
    'properties': {
        'id': parameter_types.id_string,
        'name': parameter_types.name,
        'domain': _domain_properties,
        'password': {
            'type': 'string'
        }
    },
    'required': ['password'],
    'additionalProperties': False
}

_token_properties = {
    'type': 'object',
    'properties': {
        'id': {
            'type': 'string'
        }
    },
    'required': ['id'],
    'additionalProperties': False
}


token_create = {
    'type': 'object',
    'properties': {
        'identity': {
            'type': 'object',
            'properties': {
                'methods': {
                    'type': 'array'
                },
                'password': {
                    'type': 'object',
                    'properties': {
                        'user': _user_properties
                    },
                    'required': ['user']
                },
                'token': _token_properties
            },
            'required': ['methods']
        },
        'scope': {
            'type': 'object',
            'properties': {
                'domain': _domain_properties,
                'project': _project_properties
            }
        }
    },
    'required': ['identity']
}
