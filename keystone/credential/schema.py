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

# Individual properties of the `Credential`
_credential_properties = {
    'blob': {'type': 'string'},
    'project_id': {
        'type': ['string', 'null'],
        "description": "The ID for the project. Mandatory for `EC2` type.",
    },
    'type': {'type': 'string'},
    'user_id': {'type': 'string', "format": "uuid"},
}

# Common schema of the `Credential` resource
credential_schema: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "readOnly": True},
        "links": response_types.resource_links,
        **_credential_properties,
    },
    "additionalProperties": False,
}

# Query parameters of the `/credentials` API
index_request_query: dict[str, Any] = {
    "type": "object",
    "properties": {
        "user_id": {
            "type": "string",
            "format": "uuid",
        },
        "type": {
            "type": "string",
        },
    },
}

# Response of the `/credentials` API
index_response_body: dict[str, Any] = {
    "type": "object",
    "properties": {
        "credentials": {"type": "array", "items": credential_schema},
        "links": response_types.links,
        "truncated": response_types.truncated,
    },
    "additionalProperties": False,
}

# Response of the diverse `/credentials` APIs returning single
# credential
credential_response_body: dict[str, Any] = {
    "type": "object",
    "properties": {"credential": credential_schema},
    "additionalProperties": False,
}

# Request body of the `POST /credentials` operation
create_request_body: dict[str, Any] = {
    "type": "object",
    "properties": {
        "credential": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                **_credential_properties,
            },
            "additionalProperties": False,
            "required": ["blob", "type", "user_id"],
            # Generating client code for conditionally optional parameters is
            # hard. Use if-then-else for validation keeping the schema itself
            # static.
            "if": {"properties": {"type": {"const": "ec2"}}},
            "then": {
                "title": "ec2 credential requires project_id",
                "required": ["blob", "type", "user_id", "project_id"],
            },
        }
    },
}

# Request body of the `PATCH /credentials/{credential_id}` operation
update_request_body: dict[str, Any] = {
    "type": "object",
    "properties": {
        "credential": {
            "type": "object",
            "properties": _credential_properties,
            "additionalProperties": False,
            "minProperties": 1,
        }
    },
}
