# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Common field types for validating API responses."""

from typing import Any

# Common schema for resource `link` attribute
links: dict[str, Any] = {
    "type": "object",
    "description": "Links for the collection of resources.",
    "properties": {
        "next": {"type": ["string", "null"], "format": "uri"},
        "previous": {"type": ["string", "null"], "format": "uri"},
        "self": {"type": "string", "format": "uri"},
    },
    "required": ["self"],
    "additionalProperties": False,
    "readOnly": True,
}

# Resource `links` attribute schema
resource_links: dict[str, Any] = {
    "type": "object",
    "description": "The link to the resource in question.",
    "properties": {"self": {"type": "string", "format": "uri"}},
    "additionalProperties": False,
    "readOnly": True,
}

truncated: dict[str, Any] = {
    "type": "boolean",
    "description": (
        "Flag indicating that the amount of entities exceeds global "
        "response limit"
    ),
}

tags: dict[str, Any] = {
    "type": "object",
    "properties": {
        "tags": {"type": "array", "items": {"type": "string"}},
        "links": links,
    },
    "additionalProperties": False,
}

domain_id: dict[str, Any] = {
    "type": "string",
    "minLength": 1,
    "maxLength": 64,
    "pattern": r"^[a-zA-Z0-9-]+$",
    "description": "The ID of the domain.",
}

user_id: dict[str, Any] = {
    "type": "string",
    "description": "The ID of the user.",
}

id_string: dict[str, Any] = {
    "type": "string",
    "minLength": 1,
    "maxLength": 64,
    "pattern": r"^[a-zA-Z0-9-]+$",
}

name: dict[str, Any] = {
    "type": "string",
    "minLength": 1,
    "maxLength": 255,
    "pattern": r"[\S]+",
    "description": "The resource name.",
}

datetime: dict[str, Any] = {
    "type": ["string"],
    "format": "CCYY-MM-DDThh:mm:ss.ssssssZ",
    "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z$",
    "examples": ["2015-08-27T09:49:58.000000Z"],
}
