# Copyright 2018 SUSE Linux GmbH
#
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

_role_properties = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'id': parameter_types.id_string,
            'name': parameter_types.name,
        },
        'minProperties': 1,
        'maxProperties': 1,
        'additionalProperties': False,
    },
}

# Individual properties of 'Access Rule'
_access_rules_properties = {
    "path": {
        "type": "string",
        "minLength": 0,
        "maxLength": 225,
        "pattern": r'^/\.*',
        "description": (
            "The API path that the application credential is "
            "permitted to access."
        ),
    },
    "method": {
        "type": "string",
        "pattern": r'^(POST|GET|HEAD|PATCH|PUT|DELETE)$',
        "description": (
            "The request method that the application credential is "
            "permitted to use for a given API endpoint."
        ),
    },
}

# Common schema of the `Access Rule` resource
access_rule_schema: dict[str, Any] = {
    "type": "object",
    "description": "An access rule object.",
    "properties": {
        "id": {
            "type": "string",
            "readOnly": True,
            "description": "The UUID of the access rule",
        },
        "links": response_types.resource_links,
        **_access_rules_properties,
    },
    "additionalProperties": True,
}

# Query parameters of the `/users/{user_id}/access_rules`
# or `/users/{user_id}/application_credentials` API
index_request_query: dict[str, Any] = {
    "type": "object",
    "properties": {
        "user_id": {
            "type": "string",
            "format": "uuid",
            "description": "The ID of the user who owns the resource."
        },
    },
}

# Response of the `/access_rules` API
index_response_body: dict[str, Any] = {
    "type": "object",
    "properties": {
        "access_rules": {
            "type": "array",
            "items": access_rule_schema,
            "description": "A list of access_rule objects.",
        },
        "links": response_types.links,
    },
    "additionalProperties": False,
}

# Response of `/access_rules/{access_rule_id}` API returning
# single access rule
access_rule_response_body: dict[str, Any] = {
    "type": "object",
    "description": "An access rule object.",
    "properties": {"access rule": access_rule_schema},
    "additionalProperties": True,
}

# Individual properties of 'Application Credential'
_application_credential_properties = {
    "name": {
        "type": "string",
        "description": (
            "The name of the application credential. "
            "Must be unique to a user."
        ),
    },
    "description": {
        "type": "string",
        "description": "A description of the application credential's purpose."
    },
    "expires_at": {
        "type": "string",
        "description": (
            "The expiration time of the application credential, if one "
            "was specified."
        ),
    },
    "project_id": {
        "type": "string",
        "description": (
            "The ID of the project the application credential was created for "
            "and that authentication requests using this application credential "
            "will be scoped to."
        ),
    },
    "roles": {
        "type": "array",
        "description": (
            "A list of one or more roles that this application credential has "
            "associated with its project. A token using this application credential "
            "will have these same roles."
        ),
    },
    "access_rules": {
        "type": "list",
        "description": "A lit of access_rules objects."
    },
    "unrestricted": {
        "type": "boolean",
        "description": (
            "A flag indicating whether the application credential may be used for "
            "creation or destruction of other application credentials or trusts."
        ),
    },
}

# Common schema of `Application Credential` resource
application_credential_schema: dict[str, Any] = {
    "type": "object",
    "description": "An application credential object.",
    "properties": {
        "id": {
            "type": "string",
            "readOnly": True,
            "description": "The UUID of the application credential",
        },
        "links": response_types.resource_links,
        **_application_credential_properties,
    },
    "additionalProperties": True,
}

# Response of the `/application_credentials` API
application_credential_index_response_body: dict[str, Any] = {
    "type": "object",
    "properties": {
        "application_credential": {
            "type": "array",
            "items": application_credential_schema,
            "description": "A list of application_credential objects."
        },
        "links": response_types.links,
    },
    "additionalProperties": True,
}

# Response of `/application_credentials/{application_credential_id}` 
# API returning single access rule
application_credential_response_body: dict[str, Any] = {
    "type": "object",
    "description": "An application credential object.",
    "properties": {"application credential": application_credential_schema},
    "additionalProperties": True,
}

# Request body of the `POST /application_credentials` operation
create_request_body: dict[str, Any] = {
    "type": "object",
    "description": "An application credential object.",
    "properties": {
        "application_credential": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "The UUID for the credential.",
                },
                "secret": {
                    "type": "string",
                    "description": (
                        "The secret that the application credential will be created with. "
                        "If not provided, one will be generated."
                    ),
                },
                **_application_credential_properties,
            },
            "additionalProperties": True,
        }
    }
}
