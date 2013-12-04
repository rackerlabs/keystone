# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013 OpenStack Foundation
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

from __future__ import unicode_literals

MAPPING_LARGE = {
    'name': 'large mapping',
    'rules': [{'remote': [{'type': 'orgPersonType',
                           'requirement': 'not_any_of',
                           'values': ['Contractor',
                                      'Guest']}],
               'local': {'group': 'Internal'}},
              {'remote': [{'type': 'orgPersonType',
                           'requirement': 'any_one_of',
                           'values': ['Contractor',
                                      'SubContractor']}],
               'local': {'group': 'Contractors'}},
              {'remote': [{'type': 'orgPersonType',
                           'requirement': 'any_one_of',
                           'values': ['Employee']},
                          {'type': 'sn',
                           'requirement': 'any_one_of',
                           'values': ['Young']}],
               'local': {'group': 'admin'}}]}

MAPPING_SMALL = {
    'name': 'small mapping',
    'rules': [{'remote': [{'type': 'orgPersonType',
                           'requirement': 'any_one_of',
                           'values': ['Contractor',
                                      'SubContractor']}],
               'local': {'group': 'Contractors'}}]}

MAPPING_BAD_REQ = {
    'name': 'bad requirements',
    'rules': [{'remote': [{'type': 'orgPersonType',
                           'requirement': 'bad_requirement',
                           'values': ['Contractor',
                                      'SubContractor']}],
               'local': {'group': 'Contractors'}}]}

MAPPING_BAD_VALUE = {
    'name': 'bad value',
    'rules': [{'remote': [{'type': 'orgPersonType',
                           'requirement': 'any_one_of',
                           'values': 'bad_value'}],
               'local': {'group': 'Contractors'}}]}

MAPPING_BAD_LOCAL = {
    'name': 'bad local',
    'rules': [{'remote': [{'type': 'orgPersonType',
                           'requirement': 'any_one_of',
                           'values': ['Contractor',
                                      'SubContractor']}],
               'local': {'domain.name': 'Contractors'}}]}

MAPPING_NO_RULES = {
    'name': 'no rules',
    'rules': []}

MAPPING_NO_REMOTE = {
    'name': 'no remote',
    'rules': [{'remote': [],
               'local': {'group': 'Contractors'}}]}
