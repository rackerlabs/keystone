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


class EvalType(object):
    """Store evaluation types used in mapping rules."""
    ANY_ONE_OF = 'any_one_of'
    NOT_ANY_OF = 'not_any_of'


class AssertionProcessor(object):
    """A class to process assertions and mapping rules."""

    def process(self, assertion, mapping_ref):
        """Transform assertion to a list of identity values based on a mapping

        The function will iterate through the mappings rules to find
        assertions that may be matched to a rule.

        An assertion would look like:
            {
                'Email': 'testacct@example.com',
                'UserName': 'testacct',
                'FirstName': 'Test',
                'LastName': 'Account',
                'orgPersonType': 'Tester;'
            }

        The returned data would be an array of local objects from the
        rules that were matched, for example:

        [{'group': {'id': '0cd5e9'}, 'user': {'email': 'bob@example.com'}}]

            or if there is more than one local property:

        [{'group': {'id': '123'}}, {'group': {'id': 'xyz'}}]

        """

        assertion_data = dict((n, v.split(';')) for n, v in assertion.items())

        rules = mapping_ref.get('rules')
        identity_values = []

        for rule in rules:
            direct_maps = self._verify_all_requirements(rule.get('remote'),
                                                        assertion_data)

            # If the compare comes back as None, go on to the next rule.
            if direct_maps is None:
                continue

            # Otherwise, the compare is valid, get the local rule
            local = rule.get('local')
            # If there is no direct mapping, then add it directly to the array
            # of saved values.
            if not direct_maps:
                identity_values += local
            # However, if there is direct mapping, then we need to perform
            # variable replacement.
            else:
                flat = jsonutils.dumps(local)
                # Perform the string replacement calls in reverse, just in case
                # the local values are greater than $10, then we will not
                # replace that with the value from $1.
                for (counter, value) in reversed(list(enumerate(direct_maps))):
                    target = "$%s" % counter
                    flat = flat.replace(target, value)
                ref = jsonutils.loads(flat)
                identity_values += ref

        return identity_values

    def _verify_all_requirements(self, requirements, assertion_data):
        """Go through the remote requirements and compare the assertion.

        The return value will be an array or None.
        If a value of None is returned, then go on to the next rule.
        If an array of zero length is returned, then there are no direct
        mappings to be performed.
        If the array is positive value in length, then it will store the
        values *in order* to be directly mapped.

        """

        direct_maps = []

        for requirement in requirements:
            rtype = requirement['type']
            regex = requirement.get('regex', False)

            any_one_values = requirement.get(EvalType.ANY_ONE_OF)
            if any_one_values:
                if not self._evaluate_requirement(any_one_values, rtype,
                                                  assertion_data,
                                                  EvalType.ANY_ONE_OF, regex):
                    return None

            not_any_values = requirement.get(EvalType.NOT_ANY_OF)
            if not_any_values:
                if not self._evaluate_requirement(not_any_values, rtype,
                                                  assertion_data,
                                                  EvalType.NOT_ANY_OF, regex):
                    return None

            # neither case, so it's a direct mapping
            if not not_any_values and not any_one_values:
                direct_map_value = assertion_data.get(rtype)
                if direct_map_value:
                    direct_maps += direct_map_value

        return direct_maps

    def _evaluate_requirement(self, values, rtype, assertion_data,
                              eval_type, regex):
        """Evaluate the incoming requirement and assertion.

        If the requirement type does not exist in the assertion data, then
        return False. If regex is specified, then compare the values and
        assertion values. Otherwise, grab the intersection of the values
        and use that to compare against the evaluation type.

        """

        assertion_values = assertion_data.get(rtype)
        if not assertion_values:
            return False

        if regex:
            return re.search(values[0], assertion_values[0])

        intersection = set(values).intersection(set(assertion_values))
        if intersection and eval_type == EvalType.ANY_ONE_OF:
            return True
        if not intersection and eval_type == EvalType.NOT_ANY_OF:
            return True

        return False
