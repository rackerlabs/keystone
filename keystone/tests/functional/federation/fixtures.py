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

import copy
import uuid

MAPPING = [
    {
        "local": [
            {
                "user": {
                    "name": "{0}"
                }
            },
            {
                "group": {
                    "id": "0cd5e9"
                }
            }
        ],
        "remote": [
            {
                "type": "UserName"
            },
            {
                "type": "orgPersonType",
                "any_one_of": [
                    "Contractor",
                    "SubContractor"
                ]
            }
        ]
    }
]


def randomize_mapping():
    """Return randomized copy of the MAPPING

    The only part being randomized is the effective local keystone group.

    """
    new_mapping = copy.deepcopy(MAPPING)
    new_mapping[0]['local'][0]['user'] = uuid.uuid4().hex
    return new_mapping
