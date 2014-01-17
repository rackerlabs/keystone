# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

"""Utilities for Federation Extension."""

import jsonschema

from keystone import exception
from keystone.openstack.common import jsonutils


MAPPING_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string"
        },
        "rules": {
            "minItems": 1,
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "local": {
                        "type": "array"
                    },
                    "remote": {
                        "minItems": 1,
                        "type": "array",
                        "items": {
                            "type": "object",
                            "oneOf": [
                                {"$ref": "#/definitions/empty"},
                                {"$ref": "#/definitions/any_one_of"},
                                {"$ref": "#/definitions/not_any_of"}
                            ],
                        }
                    }
                }
            }
        }
    },
    "definitions": {
        "empty": {
            "type": "object",
            "required": ['type'],
            "properties": {
                "type": {
                    "type": "string"
                },
            },
            "additionalProperties": False,
        },
        "any_one_of": {
            "type": "object",
            "additionalProperties": False,
            "required": ['type', 'any_one_of'],
            "properties": {
                "type": {
                    "type": "string"
                },
                "any_one_of": {
                    "type": "array"
                },
                "regex": {
                    "type": "boolean"
                }
            }
        },
        "not_any_of": {
            "type": "object",
            "additionalProperties": False,
            "required": ['type', 'not_any_of'],
            "properties": {
                "type": {
                    "type": "string"
                },
                "not_any_of": {
                    "type": "array"
                },
                "regex": {
                    "type": "boolean"
                }
            }
        }
    }
}


def validate_mapping_structure(ref):
        v = jsonschema.Draft4Validator(MAPPING_SCHEMA)

        messages = ''
        for error in sorted(v.iter_errors(ref), key=str):
            messages = messages + error.message + "\n"

        if messages:
            raise exception.ValidationError(messages)


"""
    A typical assertion looks like the following data:

    'ADFS_FIRSTNAME': 'Billy',
    'ADFS_GROUP': 'Domain Users;it;Direct-Employees;developer;',
    'ADFS_LASTNAME': 'Jean'

"""

def process(assertion_headers, mapping_ref):
    assertion_data = dict((n, v.split(';')) for n, v in assertion_headers.items())

    rules = mapping_ref.get('rules')
    identity_values = []

    for rule in rules:
        # go through the remote requirements and compare against the assertion
        req_valid, direct_maps = _verify_all_requirements(rule.get('remote'),
                                                          assertion_data)

        # if the compare is false, go on to the next rule
        if not req_valid:
            continue

        # get the local rule, either add it directly if no var replacement
        # is needed, otherwise do var replacement.
        local = rule.get('local')
        if not direct_maps:
            identity_values.append(local)
        else:
            flat = jsonutils.dumps(local)
            for (counter, value) in enumerate(direct_maps):
                target = "$%s" % counter
                flat = flat.replace(target, value)
            ref = jsonutils.loads(flat)
            identity_values.append(ref)

    return identity_values

def _verify_all_requirements(requirements, assertion_data):
    reqs_valid = True
    direct_maps = []

    for requirement in requirements:
        rtype = requirement['type']

        any_one_values = requirement.get('any_one_of')
        if any_one_values:
            if _any_one_of(any_one_values, rtype, assertion_data):
                reqs_valid = reqs_valid and True
            else:
                return (False, [])

        not_any_values = requirement.get('not_any_of')
        if not_any_values:
            if _not_any_of(not_any_values, rtype, assertion_data):
                reqs_valid = reqs_valid and True
            else:
                return (False, [])

        ## direct mapping
        if not not_any_values and not any_one_values:
            direct_map_value = assertion_data.get(rtype)
            if direct_map_value:
                direct_maps.append(direct_map_value)


    return (reqs_valid, direct_maps)


## consolidate these functions
def _any_one_of(values, rtype, assertion_data):
    assertion_values = assertion_data.get(rtype)
    if assertion_values:
        intersection = set(values).intersection(set(assertion_values))
        if intersection:
            return True
    return False


def _not_any_of(values, rtype, assertion_data):
    assertion_values = assertion_data.get(rtype)
    if assertion_values:
        intersection = set(values).intersection(set(assertion_values))
        if len(intersection) == 0:
            return True
    return False
