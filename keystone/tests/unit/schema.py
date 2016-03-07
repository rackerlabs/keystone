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

from keystone.common import validation
from keystone.common.validation import parameter_types


_project_v2_properties = {
    'id': parameter_types.id_string,
    'name': parameter_types.name,
    'enabled': parameter_types.boolean,
    'description': validation.nullable(parameter_types.description),
}

_token_v2_properties = {
    'audit_ids': {
        'type': 'array',
        'items': {
            'type': 'string',
        },
        'minItems': 1,
        'maxItems': 2,
    },
    'id': {'type': 'string'},
    'expires': {'type': 'string'},
    'issued_at': {'type': 'string'},
    'tenant': {
        'type': 'object',
        'properties': _project_v2_properties,
        'required': ['id', 'name', 'enabled'],
        'additionalProperties': False,
    },
}

_role_v2_properties = {
    'name': parameter_types.name,
}

_user_v2_properties = {
    'id': parameter_types.id_string,
    # TODO(jorge_munoz): Should both name and username be required?
    'name': parameter_types.name,
    'username': parameter_types.name,
    'roles': {
        'type': 'array',
        'properties': _role_v2_properties,
        'required': ['name'],
        'additionalProperties': False,
    },
    'roles_links': {
        'type': 'array',
        'items': {
            'type': 'string',
        },
    },
}

_metadata_v2_properties = {
    'is_admin': {'type': 'integer'},
    'roles': {
        'type': 'array',
        'items': {'type': 'string'},
    },
}

_endpoint_v2_properties = {
    'id': {'type': 'string'},
    'adminURL': parameter_types.url,
    'internalURL': parameter_types.url,
    'publicURL': parameter_types.url,
    'region': {'type': 'string'},
}

_service_v2_properties = {
    'type': {'type': 'string'},
    'name': parameter_types.name,
    'endpoints_links': {
        'type': 'array',
        'items': {'type': 'string'},
    },
    'endpoints': {
        'type': 'array',
        'properties': _endpoint_v2_properties,
        'required': ['publicUrl', 'id'],
        'additionalProperties': False,
    },
}

_project_v2_scope_properties = {
    'metadata': {
        'type': 'object',
        'properties': _metadata_v2_properties,
        'required': ['is_admin', 'roles'],
        'additionalProperties': False,
    },
    'serviceCatalog': {
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': _service_v2_properties,
            'required': ['endpoints', 'endpoints_links', 'name', 'type'],
            'additionalProperties': False,
        },
    },
    'token': {
        'type': 'object',
        'properties': _token_v2_properties,
        'required': ['audit_ids', 'id', 'expires', 'issued_at', 'tenant'],
        'additionalProperties': False,
    },
    'user': {
        'type': 'object',
        'properties': _user_v2_properties,
        'required': ['id', 'name', 'username', 'roles', 'roles_links'],
        'additionalProperties': False,
    },
}

scope_token_v2_schema = {
    'type': 'object',
    'properties': _project_v2_scope_properties,
    'required': ['metadata', 'user', 'serviceCatalog', 'token'],
    'optional': [],
    'additionalProperties': False,
}
