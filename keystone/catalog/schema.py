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


region_schema = {
    'type': 'object',
    'properties': {
        'description': parameter_types.description,
        # NOTE(lbragstad): If a user wants to create a region with a specific
        # value as the 'id', it is done in the request URL, e.g.
        # PUT /regions/us-east. This is not required and if an 'id' is not
        # specified in the request, Keystone will assign a uuid as the 'id'
        # for the region.
        'id': {
            'type': ['string', 'null']
        },
        'parent_region_id': {
            'type': ['string', 'null']
        },
    },
    # NOTE(lbragstad): No parameters are required for creating regions.
    'additionalProperties': True,
}

service_schema = {
    'type': 'object',
    'properties': {
        'description': parameter_types.description,
        'enabled': parameter_types.boolean,
        'name': {
            'type': 'string'
        },
        'type': {
            'type': 'string'
        }
    },
    'required': ['type'],
    'additionalProperties': True,
}

endpoint_schema = {
    'type': 'object',
    'properties': {
        'enabled': parameter_types.boolean,
        'interface': {
            'type': 'string',
            'enum': ['admin', 'internal', 'public']
        },
        'region_id': {
            'type': 'string'
        },
        'region': {
            'type': 'string'
        },
        'service_id': {
            'type': 'string'
        },
        'url': parameter_types.url
    },
    'required': ['interface', 'service_id', 'url'],
    'additionalProperties': True,
}

region_create = region_schema
region_update = region_schema
region_update['minProperties'] = 1

service_create = service_schema
service_update = service_schema
service_update['minProperties'] = 1
del service_update['required']

endpoint_create = endpoint_schema
endpoint_update = endpoint_schema
endpoint_update['minProperties'] = 1
del endpoint_update['required']
