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
from keystone.openstack.common import log


LOG = log.getLogger(__name__)


MAPPING_SCHEMA = {
    "type": "object",
    "required": ['rules'],
    "properties": {
        "rules": {
            "minItems": 1,
            "type": "array",
            "items": {
                "type": "object",
                "required": ['local', 'remote'],
                "additionalProperties": False,
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


class RuleProcessor(object):
    """A class to process assertions and mapping rules."""

    class _EvalType(object):
        """Mapping rule evaluation types."""
        ANY_ONE_OF = 'any_one_of'
        NOT_ANY_OF = 'not_any_of'

    def __init__(self, rules):
        """Initialize RuleProcessor.

        Example rules can be found at:
        :class: `keystone.tests.mapping_fixtures`

        :param rules: existing rules from a mapping
        :type rules: dict

        """

        self.rules = rules

    def process(self, assertion_data):
        """Transform assertion to a list of identity values based on
        a mapping.

        This function will iterate through the mappings rules to find
        assertions that may be matched to a rule.

        An incoming assertion looks like::

            {
                'Email': 'testacct@example.com',
                'UserName': 'testacct',
                'FirstName': 'Test',
                'LastName': 'Account',
                'orgPersonType': 'Tester;'
            }

        The expected return structure is::

            {
                'name': 'foobar',
                'group_ids': ['abc123', 'def456']
            }

        :returns: dictionary with user and group_ids

        """

        assertion = dict((n, v.split(';')) for n, v in assertion_data.items())
        identity_values = []

        for rule in self.rules:
            direct_maps = self._verify_all_requirements(rule['remote'],
                                                        assertion)

            # If the compare comes back as None, then the rule did not apply
            # to the assertion data, go on to the next rule
            if direct_maps is None:
                continue

            # Otherwise, the compare is valid, get the local rule
            local_array = rule['local']
            # If there is no direct mapping, then add it directly to the array
            # of saved values.
            if not direct_maps:
                identity_values += local_array
            # However, if there is direct mapping, then we need to perform
            # variable replacement.
            else:
                for local in local_array:
                    new_local = self._update_local_mapping(local, direct_maps)
                    identity_values.append(new_local)

        return self._format(identity_values)

    def _format(self, identity_values):
        """Refactor local mappings, to an easier to understand format.

        Refactor the incoming array to match the format needed in the
        process function. Generating content for tokens will be easier
        if some pre-processing is done at this level.

        :param identity_values: local mapping objects from valid rules
        :type identity_values: dict

        Example identity_values::

            [{'group': {'id': '0cd5e9'}, 'user': {'email': 'bob@example.com'}}]

        """

        # initialize the group_ids as a set to eliminate duplicates
        d = dict(group_ids=set())
        for x in identity_values:
            if 'user' in x:
                # if a mapping outputs more than one user name, log it
                if d.get('name') is not None:
                    LOG.warning(_('Ignoring user name %s'), x['user']['name'])
                d.setdefault('name', x['user']['name'])
            if 'group' in x:
                d['group_ids'].add(x['group']['id'])
        d['group_ids'] = list(d['group_ids'])
        return d

    def _update_local_mapping(self, local, direct_maps):
        """Replace any {0}, {1} ... values with data from the assertion.

        :returns: local mapping reference with replaced values.

        """

        new = {}
        for k, v in local.iteritems():
            if isinstance(v, dict):
                new_value = self._update_local_mapping(v, direct_maps)
            else:
                new_value = v.format(*direct_maps)
            new[k] = new_value
        return new

    def _verify_all_requirements(self, requirements, assertion):
        """Go through the remote requirements and compare the assertion.

        If a value of ``None`` is returned, this rule doesn't apply to the
        assertion data.
        If an array of zero length is returned, then there are no direct
        mappings to be performed.
        Otherwise, then it will store the values *in order* to be directly
        mapped.

        :returns: array of local mapping objects or None.

        """

        direct_maps = []

        for requirement in requirements:
            requirement_type = requirement['type']
            regex = requirement.get('regex', False)

            any_one_values = requirement.get(self._EvalType.ANY_ONE_OF)
            if any_one_values is not None:
                if not self._evaluate_requirement(any_one_values,
                                                  requirement_type,
                                                  self._EvalType.ANY_ONE_OF,
                                                  regex, assertion):
                    return None

            not_any_values = requirement.get(self._EvalType.NOT_ANY_OF)
            if not_any_values is not None:
                if not self._evaluate_requirement(not_any_values,
                                                  requirement_type,
                                                  self._EvalType.NOT_ANY_OF,
                                                  regex, assertion):
                    return None

            # If 'any_one_of' or 'not_any_of' are not found, then the values are
            # within 'type'. Attempt to find that 'type' within the assertion
            if not not_any_values and not any_one_values:
                direct_map_value = assertion.get(requirement_type)
                if direct_map_value:
                    direct_maps += direct_map_value

        return direct_maps

    def _evaluate_requirement(self, values, requirement_type,
                              eval_type, regex, assertion):
        """Evaluate the incoming requirement and assertion.

        If the requirement type does not exist in the assertion data, then
        return False. If regex is specified, then compare the values and
        assertion values. Otherwise, grab the intersection of the values
        and use that to compare against the evaluation type.

        :returns: boolean, whether requirement is valid or not.

        """

        assertion_values = assertion.get(requirement_type)
        if not assertion_values:
            return False

        if regex:
            return re.search(values[0], assertion_values[0])

        any_match = bool(set(values).intersection(set(assertion_values)))
        if any_match and eval_type == self._EvalType.ANY_ONE_OF:
            return True
        if not any_match and eval_type == self._EvalType.NOT_ANY_OF:
            return True

        return False
