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

import re

import jsonschema

from keystone import exception
from keystone.openstack.common import jsonutils


MAPPING_SCHEMA = {
    "type": "object",
    "properties": {
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
                "required": ['type'],
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


def process(assertion, mapping_ref):
    """A typical assertion looks like the following data:

    'ADFS_FIRSTNAME': 'Billy',
    'ADFS_GROUP': 'Domain Users;it;Direct-Employees;developer;',
    'ADFS_LASTNAME': 'Jean'

    """

    assertion_data = dict((n, v.split(';')) for n, v in assertion.items())

    rules = mapping_ref.get('rules')
    identity_values = []

    for rule in rules:
        # Go through the remote requirements and compare against the assertion
        # _verify_all_requirements will return a tuple, of (Boolean, Array)
        # The boolean will state whether the requirement is valid or not.
        # The array will store the value *in order* to be directly mapped
        req_valid, direct_maps = _verify_all_requirements(rule.get('remote'),
                                                          assertion_data)

        # If the compare comes back as false, go on to the next rule.
        if not req_valid:
            continue

        # Otherwise, the compare is valid, and we need to get the local rule
        # If there is no direct mapping, then add it directly to the array of
        # saved values.
        # However, if there is direct mapping, then we need to perform
        # variable replacement.
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
    direct_maps = []

    for requirement in requirements:
        rtype = requirement['type']
        regex = requirement.get('regex', False)

        # case where any_one_of is seen
        any_one_values = requirement.get('any_one_of')
        if any_one_values:
            if not _eval_req(any_one_values, rtype,
                             assertion_data, True, regex):
                return (False, [])

        # case where not_any_of is seen
        not_any_values = requirement.get('not_any_of')
        if not_any_values:
            if not _eval_req(not_any_values, rtype,
                             assertion_data, False, regex):
                return (False, [])

        # neither case, so it's a direct mapping
        if not not_any_values and not any_one_values:
            direct_map_value = assertion_data.get(rtype)
            if direct_map_value:
                direct_maps.append(direct_map_value[0])

    return (True, direct_maps)


def _eval_req(values, rtype, assertion_data, any_one_of, regex):
    assertion_values = assertion_data.get(rtype)
    if assertion_values:
        if regex:
            if not re.search(values[0], assertion_values[0]):
                return False

        intersection = set(values).intersection(set(assertion_values))
        if intersection and any_one_of:
            return True
        elif len(intersection) == 0 and not any_one_of:
            return True
    return False
