# Copyright 2017 SUSE Linux Gmbh
#
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

_registered_limit_properties = {
    'service_type': {
        'type': 'string'
    },
    'region': {
        'type': 'string'
    },
    'resource_name': {
        'type': 'string'
    },
    'project_default': {
        'type': 'integer'
    }
}

registered_limit_create_or_update = {
    'type': 'object',
    'properties': _registered_limit_properties,
    'additionalProperties': False,
    'required': ['service_type', 'region', 'resource_name', 'project_default' ]
}

_limit_properties = {
    'service_type': {
        'type': 'string'
    },
    'region': {
        'type': 'string'
    },
    'resource_name': {
        'type': 'string'
    },
    'resource_limit': {
        'type': 'integer'
    }
}

limit_create_or_update = {
    'type': 'object',
    'properties': _limit_properties,
    'additionalProperties': False,
    'required': ['service_type',
                 'region',
                 'resource_name',
                 'resource_limit' ]
}
