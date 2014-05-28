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


region_create = {
    'type': 'object',
    'properties': {
        'description': parameter_types.description,
        # NOTE(lbragstad): If a user wants to create a region with a specific
        # value as the 'id', it is done in the request URL, e.g.
        # PUT /regions/us-east. This is not required and if an 'id' is not
        # specified in the request, Keystone will assign a uuid as the 'id'
        # for the region.
        'id': {
            'type': 'string'
        },
        'parent_region_id': {
            'type': 'string'
        }
    },
    # NOTE(lbragstad): No parameters are required for creating regions.
}

region_update = {
    'type': 'object',
    'properties': {
        'description': parameter_types.description,
        'id': {
            'type': 'string'
        },
        'parent_region_id': {
            'type': 'string'
        }
    },
    'minProperties': 1,
}

service_create = {
    'type': 'object',
    'properties': {
        'description': parameter_types.description,
        'enabled': parameter_types.boolean,
        'type': {
            'type': 'string'
        },
        'name': {
            'type': 'string'
        }
    },
    'required': ['type'],
}

service_update = {
    'type': 'object',
    'properties': {
        'description': parameter_types.description,
        'enabled': parameter_types.boolean,
        'type': {
            'type': 'string'
        },
        'name': {
            'type': 'string'
        }
    },
    'minProperties': 1,
}

endpoint_create = {
    'type': 'object',
    'properties': {
        'enabled': parameter_types.boolean,
        # NOTE(lbragstad): Should 'interface' be checked against 'public',
        # 'internal', and 'admin' only instead of just string?
        'interface': {
            'type': 'string'
        },
        'region_id': {
            'type': 'string'
        },
        # Do we need both of these? Since 'region' was deprecrated in v3.2
        'region': {
            'type': 'string'
        },
        'service_id': {
            'type': 'string'
        },
        'url': parameter_types.url
    },
    'required': ['service_id', 'interface', 'url'],
}

endpoint_update = {
    'type': 'object',
    'properties': {
        'enabled': parameter_types.boolean,
        # NOTE(lbragstad): Should 'interface' be checked against 'public',
        # 'internal', and 'admin' only instead of just string?
        'interface': {
            'type': 'string'
        },
        'region_id': {
            'type': 'string'
        },
        # Do we need both of these? Since 'region' was deprecrated in v3.2
        'region': {
            'type': 'string'
        },
        'service_id': {
            'type': 'string'
        },
        'url': parameter_types.url
    },
    'minProperties': 1,
}
