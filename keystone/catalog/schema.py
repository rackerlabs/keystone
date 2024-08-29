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

from typing import Any

from keystone.api.validation import response_types
from keystone.common import validation
from keystone.common.validation import parameter_types

_region_properties = {
    'description': validation.nullable(parameter_types.description),
    # NOTE(lbragstad): Regions use ID differently. The user can specify the ID
    # or it will be generated automatically.
    'id': {'type': 'string'},
    'parent_region_id': {'type': ['string', 'null']},
}

region_create = {
    'type': 'object',
    'properties': _region_properties,
    'additionalProperties': True,
    # NOTE(lbragstad): No parameters are required for creating regions.
}

region_update = {
    'type': 'object',
    'properties': _region_properties,
    'minProperties': 1,
    'additionalProperties': True,
}

# Schema for Service v3
# Individual properties of 'Service'
_service_properties = {
    "enabled": {
        "type": "boolean",
        "description": (
            "Defines whether the service and its endpoints appear in the "
            "service catalog - false. The service and its endpoints do "
            "not appear in the service catalog - true."
        ),
    },
    "type": {
        "type": "string",
        "description": (
            "The service type, which describes the API implemented by the "
            "service. Value is compute, ec2, identity, image, network, "
            "or volume."
        ),
        "minLength": 1,
        "maxLength": 255,
    },
}

_service_name_properties = {
    "name": {
        "type": "string",
        "description": "The service name.",
        "minLength": 1,
        "maxLength": 255,
    },
}

# Common schema of `Service` resource
service_schema: dict[str, Any] = {
    "type": "object",
    "description": "A service object",
    "properties": {
        "id": {
            "type": "string",
            "readOnly": True,
            "description": (
                "The UUID of the service to which the endpoint belongs."
            ),
        },
        "name": {
            "type": "string",
            "description": "The service name.",
            "minLength": 0,
            "maxLength": 255,
        },
        "links": response_types.resource_links,
        **_service_properties,
    },
    "additionalProperties": True,
}

# Query parameters of the `/services` API
service_index_request_query: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": True,
}

# Response of the `/services` API
service_index_response_body: dict[str, Any] = {
    "type": "object",
    "properties": {
        "services": {
            "type": "array",
            "items": service_schema,
            "description": "A list of service object.",
        },
        "links": response_types.links,
        "truncated": response_types.truncated,
    },
    "additionalProperties": True,
}

# Response of the `/services` API returning a single service
service_response_body: dict[str, Any] = {
    "type": "object",
    "description": "A service object.",
    "properties": {"service": service_schema},
    "additionalProperties": False,
}

# Request body of the `POST /services` operation
service_create_request_body: dict[str, Any] = {
    "type": "object",
    "description": "A service object.",
    "properties": {
        "service": {
            "type": "object",
            "properties": {
                **_service_properties,
                **_service_name_properties,
            },
            "additionalProperties": True,
            "required": ["type"],
        }
    },
}

# Request body of the `PATCH /services/{service_id}` operation
service_update_request_body: dict[str, Any] = {
    "type": "object",
    "description": "A service object.",
    "properties": {
        "service": {
            "type": "object",
            "properties": {
                **_service_properties,
                **_service_name_properties,
            },
            "additionalProperties": True,
            "minProperties": 1,
        },
    },
    "required": ["service"],
}

_endpoint_properties = {
    'enabled': parameter_types.boolean,
    'interface': {'type': 'string', 'enum': ['admin', 'internal', 'public']},
    'region_id': {'type': 'string'},
    'region': {'type': 'string'},
    'service_id': {'type': 'string'},
    'url': parameter_types.url,
}

endpoint_create = {
    'type': 'object',
    'properties': _endpoint_properties,
    'required': ['interface', 'service_id', 'url'],
    'additionalProperties': True,
}

endpoint_update = {
    'type': 'object',
    'properties': _endpoint_properties,
    'minProperties': 1,
    'additionalProperties': True,
}

_endpoint_group_properties = {
    'description': validation.nullable(parameter_types.description),
    'filters': {'type': 'object'},
    'name': parameter_types.name,
}

endpoint_group_create = {
    'type': 'object',
    'properties': _endpoint_group_properties,
    'required': ['name', 'filters'],
}

endpoint_group_update = {
    'type': 'object',
    'properties': _endpoint_group_properties,
    'minProperties': 1,
}
